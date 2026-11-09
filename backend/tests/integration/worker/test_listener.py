"""LISTEN 접속 — 커밋된 pg_notify 만 깨우고, (재)접속 직후에는 한 번 강제로 깨우며, 서버가 끊으면 다시 잇는다.

실제 Postgres(테스트 DB)를 상대로 돈다. 알림은 커밋 때 전달되므로 롤백되는 `db_session` 이 아니라 커밋하는 세션을 따로 연다.
"""

import asyncio
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.worker.listener import Listener, listen_dsn
from app.worker.notify import notify


async def _notify_committed(engine: AsyncEngine, channel: str) -> None:
    async with AsyncSession(engine) as session, session.begin():
        await notify(session, channel)


async def test_only_committed_notifications_wake_and_connecting_forces_one_poll(db_engine: AsyncEngine) -> None:
    channel = f"app_test_{uuid4().hex[:8]}"
    wake, stop = asyncio.Event(), asyncio.Event()
    listener = Listener(listen_dsn(), {channel: wake}, reconnect_seconds=0.1)
    task = asyncio.create_task(listener.run(stop))
    try:
        await asyncio.wait_for(listener.connected.wait(), 5)
        # 접속 직후 강제 폴링 — 워커가 떠 있지 않던 동안 쌓인 행을 집게 한다
        assert wake.is_set()
        wake.clear()

        # 롤백된 알림은 오지 않는다
        async with AsyncSession(db_engine) as session:
            await notify(session, channel)
            await session.rollback()
        await asyncio.sleep(0.2)
        assert not wake.is_set()

        # 커밋된 알림은 온다
        await _notify_committed(db_engine, channel)
        await asyncio.wait_for(wake.wait(), 5)
    finally:
        stop.set()
        await asyncio.wait_for(task, 5)
    assert not listener.connected.is_set()


async def test_reconnects_when_the_server_drops_the_connection(db_engine: AsyncEngine) -> None:
    channel = f"app_test_{uuid4().hex[:8]}"
    wake, stop = asyncio.Event(), asyncio.Event()
    listener = Listener(listen_dsn(), {channel: wake}, reconnect_seconds=0.1)
    task = asyncio.create_task(listener.run(stop))
    try:
        await asyncio.wait_for(listener.connected.wait(), 5)
        first_pid = listener.server_pid
        assert first_pid is not None
        wake.clear()

        async with db_engine.connect() as connection:
            await connection.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": first_pid})

        # 끊긴 뒤 다시 잇고, 재접속 직후 다시 한 번 깨운다
        deadline = asyncio.get_running_loop().time() + 5
        while not (listener.connected.is_set() and listener.server_pid not in (None, first_pid)):
            assert asyncio.get_running_loop().time() < deadline, "재접속하지 않았다"
            await asyncio.sleep(0.05)
        await asyncio.wait_for(wake.wait(), 5)

        # 재접속한 접속으로도 알림이 온다
        wake.clear()
        await _notify_committed(db_engine, channel)
        await asyncio.wait_for(wake.wait(), 5)
    finally:
        stop.set()
        await asyncio.wait_for(task, 5)
