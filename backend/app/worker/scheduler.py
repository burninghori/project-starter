"""주기 작업 — 시작하자마자 한 번, 그 뒤 간격마다(고아 회수 · 만료 배치 정리).

한 번의 실패가 주기를 멈추지 않는다 — 예외는 로그로 남기고 다음 차례를 기다린다(실패 사유 보존). `stop` 이 켜지면 바로 끝난다.
"""

import asyncio
import contextlib
from collections.abc import Awaitable, Callable

from ..logging import get_logger

logger = get_logger("worker.scheduler")


async def sleep_or_stop(stop: asyncio.Event, seconds: float) -> None:
    """`seconds` 만큼 기다리되 `stop` 이 켜지면 바로 돌아온다."""
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=seconds)


async def every(name: str, interval_seconds: float, fn: Callable[[], Awaitable[None]], stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await fn()
        except Exception:
            logger.exception("periodic job failed", extra={"job": name, "interval_seconds": interval_seconds})
        await sleep_or_stop(stop, interval_seconds)
