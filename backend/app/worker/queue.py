"""작업 큐 소비 루프 — Postgres 작업 행을 집어 처리한다(결정 0005, api.md 「워커」).

행의 모양·집는 SQL·완료 펜싱·고아 회수는 도메인이 `ConsumerSpec` 으로 준다(작업 함수는 도메인 폴더에). 이 모듈은 **언제 집고
몇 개를 동시에 돌리고 언제 멈추는지**만 안다.

- 깨우기: 채널의 `asyncio.Event`(LISTEN 알림, `listener.py`) 또는 보조 폴링 간격. 깨어나면 집을 것이 없을 때까지 반복해 집는다.
  알림이 집는 도중에 오면 Event 가 남아 바로 다음 바퀴를 돈다(놓치지 않는다).
- 동시 처리: 한 번에 집는 수 = 빈자리(동시 처리 수 − 진행 중). 작업은 태스크로 돌린다.
- 실패: `process` 의 예외는 로그로 남기고 루프는 계속 돈다 — 행에 사유를 적고 재시도 여부를 정하는 것은 도메인 `process` 의 일이다.
  `claim` 의 예외(DB 접속 등)도 로그로 남기고 다음 폴링을 기다린다.
- 종료: `stop` 이 켜지면 더 집지 않고 진행 중 작업을 기다린다.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ..logging import get_logger
from .scheduler import every

logger = get_logger("worker.queue")

# 세션을 여는 법 — 워커는 `app.db.engine.session_scope`, 테스트는 가짜
SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


@dataclass(frozen=True, slots=True)
class Job:
    """집은 작업 행 하나. `attempt` 는 집을 때의 값 — 완료 UPDATE 가 이 값으로 펜싱한다."""

    id: int
    attempt: int


@dataclass(frozen=True, slots=True)
class ConsumerSpec:
    """도메인이 끼우는 소비자 하나."""

    # 로그·태스크 이름
    name: str
    # LISTEN 채널 — 상수는 도메인 모듈이 가진다
    channel: str
    # `FOR UPDATE SKIP LOCKED LIMIT n` 으로 집어 집힌 표시(claimed_at·attempt+1)를 하고 커밋한다. 없으면 []
    # n 건을 넘겨 집으면 안 된다(동시 처리 수가 이 값으로 지켜진다) — 집을 행은 CTE 에서 한 번만 고른다(api.md 「워커」)
    claim: Callable[[AsyncSession, int], Awaitable[list[Job]]]
    # 작업 1건. 세션은 안에서 연다(한 작업 = 한 트랜잭션). 완료 UPDATE 는 집을 때의 attempt 로 펜싱한다
    process: Callable[[Job], Awaitable[None]]
    # 집힌 지 `orphan_after` 가 지난 행을 되돌리고(상한이면 실패로), 되돌린 수를 돌려준다
    reclaim: Callable[[AsyncSession, timedelta, int], Awaitable[int]]


async def run_consumer(
    spec: ConsumerSpec,
    *,
    wake: asyncio.Event,
    stop: asyncio.Event,
    concurrency: int,
    poll_seconds: float,
    open_session: SessionFactory,
) -> None:
    inflight: set[asyncio.Task[None]] = set()
    try:
        while not stop.is_set():
            wake.clear()
            try:
                await _drain(spec, inflight, concurrency=concurrency, open_session=open_session, stop=stop)
            except Exception:
                logger.exception("claim failed — waiting for the next poll", extra={"consumer": spec.name})
            await _wait_for_wake(wake, stop, timeout=poll_seconds)
    finally:
        if inflight:
            logger.info("waiting for in-flight jobs", extra={"consumer": spec.name, "count": len(inflight)})
            await asyncio.gather(*inflight, return_exceptions=True)


async def _drain(
    spec: ConsumerSpec,
    inflight: set[asyncio.Task[None]],
    *,
    concurrency: int,
    open_session: SessionFactory,
    stop: asyncio.Event,
) -> None:
    """빈자리만큼 집어 돌리기를, 집을 것이 없을 때까지."""
    while not stop.is_set():
        free = concurrency - len(inflight)
        if free <= 0:
            await asyncio.wait(set(inflight), return_when=asyncio.FIRST_COMPLETED)
            continue
        async with open_session() as db:
            jobs = await spec.claim(db, free)
        if not jobs:
            return
        for job in jobs:
            task = asyncio.create_task(_run_job(spec, job), name=f"{spec.name}:{job.id}")
            inflight.add(task)
            task.add_done_callback(inflight.discard)


async def _run_job(spec: ConsumerSpec, job: Job) -> None:
    try:
        await spec.process(job)
    except Exception:
        logger.exception("job failed", extra={"consumer": spec.name, "job_id": job.id, "attempt": job.attempt})


async def _wait_for_wake(wake: asyncio.Event, stop: asyncio.Event, *, timeout: float) -> None:
    """깨우기·종료 중 먼저 오는 것까지, 늦어도 `timeout` 까지 기다린다."""
    waiters = [asyncio.create_task(wake.wait()), asyncio.create_task(stop.wait())]
    try:
        await asyncio.wait(waiters, timeout=timeout, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for waiter in waiters:
            waiter.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)


async def run_reclaimer(
    consumers: Sequence[tuple[ConsumerSpec, timedelta]],
    *,
    stop: asyncio.Event,
    interval_seconds: float,
    max_attempts: int,
    open_session: SessionFactory,
) -> None:
    """고아 회수 주기 작업 — 소비자마다 그 소비자의 회수 기준(`orphan_after`)으로 `reclaim` 을 부른다.

    되돌린 것이 있으면 경고로 남긴다(워커가 죽었거나 처리가 실패한 신호). 회수는 알림을 보내지 않으므로 되돌아간 작업은 보조 폴링이 집는다.
    한 소비자의 회수가 실패해도 다른 소비자의 회수는 한다 — 사유는 로그로 남기고 다음 차례에 다시 시도된다.
    """

    async def reclaim_all() -> None:
        for spec, orphan_after in consumers:
            try:
                async with open_session() as db:
                    count = await spec.reclaim(db, orphan_after, max_attempts)
            except Exception:
                logger.exception("reclaim failed", extra={"consumer": spec.name})
                continue
            if count:
                logger.warning("reclaimed orphan jobs", extra={"consumer": spec.name, "count": count})

    await every("reclaim", interval_seconds, reclaim_all, stop)
