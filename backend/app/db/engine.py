"""DB 엔진·세션의 단일 출처.

앱 lifespan 이 `init_engine()` 으로 엔진을 만들고 `dispose_engine()` 으로 닫는다. 요청 핸들러는
`DbDep`(db/deps.py)으로, 워커·스크립트는 `session_scope()` 로 세션을 얻는다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def database_url(*, user: str | None = None, password: str | None = None, database: str | None = None) -> URL:
    """설정의 접속 좌표로 asyncpg URL 을 만든다. 테스트·마이그레이션은 계정·DB 이름만 바꿔 쓴다."""
    return URL.create(
        "postgresql+asyncpg",
        username=user if user is not None else settings.db_user,
        password=password if password is not None else settings.db_password.get_secret_value(),
        host=settings.db_host,
        port=settings.db_port,
        database=database if database is not None else settings.db_name,
    )


def init_engine(url: URL | None = None) -> AsyncEngine:
    global _engine, _sessionmaker
    if _engine is not None:
        raise RuntimeError("DB 엔진이 이미 초기화됐다")
    _engine = create_async_engine(url or database_url(), pool_pre_ping=True)
    _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("DB 엔진이 초기화되지 않았다 — 앱 lifespan 또는 init_engine() 을 먼저 거친다")
    return _engine


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """성공하면 commit, 예외면 rollback 하는 세션 하나."""
    if _sessionmaker is None:
        raise RuntimeError("DB 엔진이 초기화되지 않았다 — 앱 lifespan 또는 init_engine() 을 먼저 거친다")
    async with _sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
