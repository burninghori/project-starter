import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# side-effect import — 모든 도메인 모델이 Base.metadata 에 등록돼야 autogenerate 가 테이블을 본다
from app.db import model_registry as _model_registry  # noqa: F401
from app.db.base import Base
from app.db.engine import database_url
from migrations.app_role import app_role_credentials, ensure_app_role

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers 기본값(True)은 이 시점에 이미 만들어진 앱 로거(`app.*`)를 꺼 버린다 — 같은 프로세스에서
    # 마이그레이션을 돌리는 테스트에서 그 뒤의 로그 단언이 조용히 깨진다. 배포의 마이그레이션 작업은 혼자 돌아 영향이 없다
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """SQL 미리보기(`alembic upgrade head --sql`). 앱 롤 정비는 실제 DB 가 있어야 해서 렌더하지 않는다."""
    context.configure(
        url=database_url().render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection, app_user: str, app_password: str) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
        # revision 적용과 같은 트랜잭션. 적용할 revision 이 없어도 권한은 다시 맞춘다.
        ensure_app_role(connection, app_user, app_password)


async def run_migrations_online() -> None:
    # 접속 계정은 이 프로세스의 DB_USER·DB_PASSWORD 다 — 마이그레이션은 스키마 변경 권한이 있는 계정으로 돈다.
    app_user, app_password = app_role_credentials()
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations, app_user, app_password)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
