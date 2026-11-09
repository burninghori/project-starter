"""주기 작업 — 시작하자마자 한 번, 그 뒤 간격마다. 한 번의 실패가 주기를 멈추지 않고, 종료는 기다리던 간격을 끊는다."""

import asyncio
import logging

import pytest

from app.worker.scheduler import every, sleep_or_stop


async def test_runs_immediately_then_every_interval_and_survives_failures(caplog: pytest.LogCaptureFixture) -> None:
    calls: list[int] = []
    stop = asyncio.Event()

    async def job() -> None:
        calls.append(len(calls) + 1)
        if len(calls) == 2:
            raise RuntimeError("두 번째는 실패(가짜)")

    with caplog.at_level(logging.ERROR, logger="app.worker.scheduler"):
        task = asyncio.create_task(every("fake", 0.03, job, stop))
        await asyncio.sleep(0.2)
        stop.set()
        await asyncio.wait_for(task, 2)

    assert len(calls) >= 3  # 즉시 1회 + 간격마다, 실패 뒤에도 계속
    failures = [record for record in caplog.records if record.getMessage() == "periodic job failed"]
    assert len(failures) == 1 and failures[0].exc_info is not None


async def test_stop_cuts_the_wait_short() -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.call_later(0.02, stop.set)

    started = loop.time()
    await sleep_or_stop(stop, 60)

    assert loop.time() - started < 1.0
