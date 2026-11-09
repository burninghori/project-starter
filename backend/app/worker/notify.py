"""API 가 작업 행을 만든 트랜잭션 안에서 워커를 깨우는 알림(결정 0005).

Postgres 는 NOTIFY 를 **커밋 때** 전달하고 롤백이면 보내지 않는다 — 커밋 뒤에 따로 보낼 필요가 없고, 행 없이 알림만 가는 일도 없다.
페이로드는 비운다. 행 상태가 정본이고 알림은 깨우는 신호일 뿐이다(워커는 깨어나면 집을 것이 없을 때까지 집는다).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def notify(db: AsyncSession, channel: str) -> None:
    """같은 트랜잭션의 `pg_notify(channel, '')`. 채널 이름은 소비자가 가진 상수를 쓴다(`ConsumerSpec.channel`)."""
    await db.execute(text("SELECT pg_notify(:channel, '')"), {"channel": channel})
