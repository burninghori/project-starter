"""LISTEN 전용 접속 — API 가 작업 행을 커밋하며 보낸 `pg_notify` 를 받아 소비자를 깨운다(결정 0005).

- 풀에서 빌리지 않고 asyncpg 접속 하나를 따로 연다. 커넥션 풀러(PgBouncer transaction 모드 등)를 도입해도 이 접속만 우회시키면 된다.
- 끊기면 다시 잇고, (재)접속 직후 **모든 채널의 Event 를 켠다** — 끊긴 사이의 알림은 잃었으므로 한 번 집게 한다.
- 페이로드는 쓰지 않는다. 행 상태가 정본이고 알림은 깨우는 신호다.
"""

import asyncio
from collections.abc import Mapping
from functools import partial
from typing import Any

import asyncpg

from ..db.engine import database_url
from ..logging import get_logger
from .scheduler import sleep_or_stop

logger = get_logger("worker.listener")

# asyncpg 기본 접속 대기(60초)는 그동안 종료 신호를 보지 못한다. 정상 접속은 1초 안쪽이고, 실패하면 reconnect_seconds 뒤 다시 하므로
# 10초면 충분하다 — 종료가 늦어지는 최대치도 10초라 흔한 컨테이너 중지 유예(30초) 안에 든다
CONNECT_TIMEOUT_SECONDS = 10


def listen_dsn() -> str:
    """앱 설정의 접속 좌표로 asyncpg DSN 을 만든다(SQLAlchemy 드라이버 접두사 없이)."""
    return database_url().set(drivername="postgresql").render_as_string(hide_password=False)


class _ConnectionLostError(Exception):
    """서버가 접속을 끊었다(장애·재시작·`pg_terminate_backend`)."""


def _on_notify(event: asyncio.Event, _connection: Any, _pid: int, channel: str, _payload: str) -> None:
    logger.debug("notification received", extra={"channel": channel})
    event.set()


class Listener:
    """채널마다 `asyncio.Event` 하나 — 알림이 오면 켠다. `connected` 는 LISTEN 을 걸어 둔 동안 켜져 있다(진단·테스트용)."""

    def __init__(self, dsn: str, wakeups: Mapping[str, asyncio.Event], *, reconnect_seconds: float = 5.0) -> None:
        self._dsn = dsn
        self._wakeups = dict(wakeups)
        self._reconnect_seconds = reconnect_seconds
        self.connected = asyncio.Event()
        # 접속의 서버 프로세스 id — 테스트가 접속을 끊어 재접속을 확인할 때
        self.server_pid: int | None = None

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await self._serve(stop)
            except (
                _ConnectionLostError,
                TimeoutError,
                OSError,
                asyncpg.PostgresError,
                asyncpg.InterfaceError,
            ) as exc:
                logger.warning(
                    "listener disconnected — reconnecting",
                    extra={"error": f"{type(exc).__name__}: {exc}", "retry_seconds": self._reconnect_seconds},
                )
                await sleep_or_stop(stop, self._reconnect_seconds)

    async def _serve(self, stop: asyncio.Event) -> None:
        connection = await asyncpg.connect(self._dsn, timeout=CONNECT_TIMEOUT_SECONDS)
        lost = asyncio.Event()
        try:
            connection.add_termination_listener(lambda _connection: lost.set())
            for channel, event in self._wakeups.items():
                await connection.add_listener(channel, partial(_on_notify, event))
            # 끊긴 사이의 알림은 잃었다 — 한 번 집게 한다(처음 접속도 마찬가지: 워커가 떠 있지 않던 동안 쌓인 행)
            for event in self._wakeups.values():
                event.set()
            self.server_pid = connection.get_server_pid()
            self.connected.set()
            logger.info("listener connected", extra={"channels": sorted(self._wakeups), "server_pid": self.server_pid})
            await _wait_any(lost, stop)
            if lost.is_set() and not stop.is_set():
                raise _ConnectionLostError("server closed the LISTEN connection")
        finally:
            self.connected.clear()
            self.server_pid = None
            try:
                await connection.close(timeout=5)
            except (OSError, asyncpg.PostgresError, asyncpg.InterfaceError) as exc:
                logger.debug("listener close failed (already gone)", extra={"error": str(exc)})


async def _wait_any(*events: asyncio.Event) -> None:
    waiters = [asyncio.create_task(event.wait()) for event in events]
    try:
        await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for waiter in waiters:
            waiter.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
