"""소비 루프 — 깨우면 빌 때까지 집고, 폴링으로도 집고, 동시 처리 수를 지키고, 실패해도 멈추지 않고, 종료는 진행 중 작업을 기다린다.

작업 행은 없다 — 가짜 `ConsumerSpec` 이 메모리 목록에서 집는다. 세션도 열지 않는다(가짜 세션 팩토리).
"""

import asyncio
import logging
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.queue import ConsumerSpec, Job, run_consumer, run_reclaimer


@asynccontextmanager
async def no_session() -> AsyncIterator[AsyncSession]:
    yield cast(AsyncSession, None)


class FakeQueue:
    """집을 작업 목록과 처리 기록. `process` 는 `job_seconds` 만큼 잠들고, `failing` 에 든 id 는 예외를 낸다."""

    def __init__(self, job_ids: list[int], *, job_seconds: float = 0.0, failing: set[int] | None = None) -> None:
        self.pending = deque(Job(id=job_id, attempt=1) for job_id in job_ids)
        self.job_seconds = job_seconds
        self.failing = failing if failing is not None else set()
        self.processed: list[int] = []
        self.running = 0
        self.max_running = 0
        self.claim_calls = 0
        self.claim_failures_left = 0
        self.reclaim_calls = 0
        self.reclaim_error: Exception | None = None

    async def claim(self, _db: AsyncSession, limit: int) -> list[Job]:
        self.claim_calls += 1
        if self.claim_failures_left > 0:
            self.claim_failures_left -= 1
            raise RuntimeError("DB 접속 실패(가짜)")
        jobs = [self.pending.popleft() for _ in range(min(limit, len(self.pending)))]
        return jobs

    async def process(self, job: Job) -> None:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            await asyncio.sleep(self.job_seconds)
            if job.id in self.failing:
                raise RuntimeError(f"작업 {job.id} 실패(가짜)")
            self.processed.append(job.id)
        finally:
            self.running -= 1

    async def reclaim(self, _db: AsyncSession, _orphan_after: timedelta, _max_attempts: int) -> int:
        self.reclaim_calls += 1
        if self.reclaim_error is not None:
            raise self.reclaim_error
        return 2 if self.reclaim_calls == 1 else 0

    def spec(self) -> ConsumerSpec:
        return ConsumerSpec(
            name="fake", channel="app_fake", claim=self.claim, process=self.process, reclaim=self.reclaim
        )


async def _until(predicate: Callable[[], bool], *, timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("기다리던 상태가 되지 않았다")
        await asyncio.sleep(0.01)


def _start(
    queue: FakeQueue, *, concurrency: int, poll_seconds: float
) -> tuple[asyncio.Task[None], asyncio.Event, asyncio.Event]:
    wake, stop = asyncio.Event(), asyncio.Event()
    task = asyncio.create_task(
        run_consumer(
            queue.spec(),
            wake=wake,
            stop=stop,
            concurrency=concurrency,
            poll_seconds=poll_seconds,
            open_session=no_session,
        )
    )
    return task, wake, stop


async def test_wake_drains_the_queue_within_the_concurrency_limit() -> None:
    queue = FakeQueue([1, 2, 3, 4, 5], job_seconds=0.02)
    task, wake, stop = _start(queue, concurrency=2, poll_seconds=60)

    wake.set()
    await _until(lambda: len(queue.processed) == 5)
    stop.set()
    await asyncio.wait_for(task, 2)

    assert sorted(queue.processed) == [1, 2, 3, 4, 5]
    assert queue.max_running == 2
    # 빌 때까지 집는다 — 마지막 claim 이 빈 목록을 돌려줘야 바퀴가 끝난다
    assert queue.claim_calls >= 3


async def test_backup_poll_claims_without_a_notification() -> None:
    queue = FakeQueue([], job_seconds=0.0)
    task, _wake, stop = _start(queue, concurrency=1, poll_seconds=0.05)

    await _until(lambda: queue.claim_calls >= 1)
    queue.pending.append(Job(id=7, attempt=1))
    await _until(lambda: queue.processed == [7])
    stop.set()
    await asyncio.wait_for(task, 2)


async def test_a_failing_job_is_logged_and_the_loop_goes_on(caplog: pytest.LogCaptureFixture) -> None:
    queue = FakeQueue([1, 2, 3], failing={2})
    task, wake, stop = _start(queue, concurrency=1, poll_seconds=60)

    with caplog.at_level(logging.ERROR, logger="app.worker.queue"):
        wake.set()
        await _until(lambda: sorted(queue.processed) == [1, 3])
    stop.set()
    await asyncio.wait_for(task, 2)

    failed = [record for record in caplog.records if record.getMessage() == "job failed"]
    assert len(failed) == 1
    assert failed[0].exc_info is not None
    assert getattr(failed[0], "job_id", None) == 2


async def test_a_failing_claim_is_logged_and_retried_on_the_next_poll(caplog: pytest.LogCaptureFixture) -> None:
    queue = FakeQueue([1])
    queue.claim_failures_left = 1
    task, _wake, stop = _start(queue, concurrency=1, poll_seconds=0.05)

    with caplog.at_level(logging.ERROR, logger="app.worker.queue"):
        await _until(lambda: queue.processed == [1])
    stop.set()
    await asyncio.wait_for(task, 2)

    assert any(record.getMessage().startswith("claim failed") for record in caplog.records)


async def test_stop_waits_for_in_flight_jobs() -> None:
    queue = FakeQueue([1], job_seconds=0.2)
    task, wake, stop = _start(queue, concurrency=1, poll_seconds=60)

    wake.set()
    await _until(lambda: queue.running == 1)
    stop.set()
    await asyncio.wait_for(task, 2)

    assert queue.processed == [1]


async def test_reclaimer_runs_right_away_and_then_every_interval() -> None:
    queue = FakeQueue([])
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_reclaimer(
            [(queue.spec(), timedelta(minutes=10))],
            stop=stop,
            interval_seconds=0.05,
            max_attempts=3,
            open_session=no_session,
        )
    )

    await _until(lambda: queue.reclaim_calls >= 3)
    stop.set()
    await asyncio.wait_for(task, 2)


async def test_one_consumers_reclaim_failure_does_not_skip_the_others(caplog: pytest.LogCaptureFixture) -> None:
    """앞 소비자의 회수가 예외를 내도 뒤 소비자의 회수는 같은 바퀴에서 돈다 — 사유는 로그에 남는다."""
    broken, healthy = FakeQueue([]), FakeQueue([])
    broken.reclaim_error = RuntimeError("회수 SQL 실패(가짜)")
    stop = asyncio.Event()
    with caplog.at_level(logging.ERROR, logger="app.worker.queue"):
        task = asyncio.create_task(
            run_reclaimer(
                [(broken.spec(), timedelta(minutes=10)), (healthy.spec(), timedelta(minutes=2))],
                stop=stop,
                interval_seconds=0.05,
                max_attempts=3,
                open_session=no_session,
            )
        )
        await _until(lambda: healthy.reclaim_calls >= 2)
        stop.set()
        await asyncio.wait_for(task, 2)

    assert broken.reclaim_calls >= 2  # 실패해도 다음 바퀴에 다시 시도한다
    failed = [record for record in caplog.records if record.getMessage() == "reclaim failed"]
    assert failed and getattr(failed[0], "consumer", None) == "fake"
