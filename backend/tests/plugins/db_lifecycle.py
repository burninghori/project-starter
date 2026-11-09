"""테스트 DB 수명 — 세션당 한 번 새로 만들고 마이그레이션을 적용, 테스트마다 롤백.

- `migrated_database` (session): `app_test` 를 지우고 다시 만든 뒤 `alembic upgrade head`.
  실제 배포와 같은 마이그레이션 경로를 타므로 모델과 마이그레이션이 어긋나면 여기서 드러난다.
- `db_engine` (function): 테스트 DB 엔진. 연결 풀 없이(NullPool) 테스트마다 새로 만든다.
- `db_session` (function): 바깥 트랜잭션 안의 세션. 코드가 commit 해도 savepoint 까지만 가고,
  테스트가 끝나면 바깥 트랜잭션을 롤백해 다음 테스트에 데이터가 남지 않는다.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.engine import database_url

BACKEND_DIR = Path(__file__).resolve().parents[2]


async def _recreate_database(name: str) -> None:
    # CREATE/DROP DATABASE 는 트랜잭션 밖에서 돈다(AUTOCOMMIT). 접속은 관리용 postgres DB 로.
    admin = create_async_engine(database_url(database="postgres"), isolation_level="AUTOCOMMIT", poolclass=NullPool)
    try:
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        await admin.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[str]:
    name = settings.db_name
    if not name.endswith("_test"):
        raise RuntimeError(f"테스트 DB 이름은 _test 로 끝나야 한다(지우고 다시 만든다): {name}")
    asyncio.run(_recreate_database(name))
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")
    yield name


@pytest.fixture
async def db_engine(migrated_database: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
