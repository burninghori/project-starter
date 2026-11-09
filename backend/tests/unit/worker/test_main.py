"""진입점의 종료 처리 — `stop` 으로 끝난 태스크는 죽은 게 아니고, 예외로 끝났거나 신호 없이 돌아온 태스크는 죽은 것이다."""

import asyncio
import logging

import pytest

from app.worker.__main__ import _run_until_stop


async def _until(stop: asyncio.Event) -> None:
    await stop.wait()


async def _crash() -> None:
    raise RuntimeError("가짜 장애")


async def _return_without_stop() -> None:
    return None


async def test_tasks_finishing_on_the_stop_signal_are_not_deaths() -> None:
    """stop 과 같은 틱에 끝난 태스크(재접속 대기 중 SIGTERM 을 받은 리스너)를 죽은 것으로 보지 않는다."""
    stop = asyncio.Event()
    task = asyncio.create_task(_until(stop), name="listener")
    asyncio.get_running_loop().call_later(0.01, stop.set)
    await _run_until_stop([task], stop)
    assert task.done() and task.exception() is None


async def test_a_crashed_task_stops_the_rest_and_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    stop = asyncio.Event()
    survivor = asyncio.create_task(_until(stop), name="consumer:fake")
    crashed = asyncio.create_task(_crash(), name="listener")
    with caplog.at_level(logging.ERROR, logger="app.worker"), pytest.raises(RuntimeError, match="listener"):
        await _run_until_stop([crashed, survivor], stop)
    assert stop.is_set() and survivor.done()
    died = [record for record in caplog.records if record.getMessage() == "worker task died"]
    assert [getattr(record, "task", None) for record in died] == ["listener"]


async def test_a_task_returning_without_a_stop_signal_is_a_death() -> None:
    stop = asyncio.Event()
    task = asyncio.create_task(_return_without_stop(), name="periodic:purge")
    with pytest.raises(RuntimeError, match="periodic:purge"):
        await _run_until_stop([task], stop)
