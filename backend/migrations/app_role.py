"""런타임 앱 DB 롤의 생성과 권한 정비 — 매 `alembic upgrade head` 의 마지막 단계.

마이그레이션은 스키마를 바꿀 수 있는 계정(배포는 DB 관리자 계정, 로컬은 postgres)으로 돌고,
앱(api·worker)은 데이터 읽기·쓰기만 되는 앱 롤로 돈다. 그 앱 롤을 여기서 만들고 비밀번호를 맞춘 뒤
현재 테이블·시퀀스 권한과 이후 생길 객체의 기본 권한을 준다.

앱 롤 계정은 `APP_DB_USER`·`APP_DB_PASSWORD` 로 받는다(배포는 비밀 저장소가 마이그레이션 작업에 주입한다). 앱 설정
(`app.config`)이 아니라 마이그레이션만의 입력이라 여기서 직접 읽는다. 빠지면 실패한다(기조 5).
"""

import os

from sqlalchemy import text
from sqlalchemy.engine import Connection

# 앱 롤이 더하기만 하는 표(감사 기록 등) — UPDATE · DELETE 권한을 주지 않는다. 표를 만드는 PR 이 이름을 한 줄 더한다
APPEND_ONLY_TABLES: tuple[str, ...] = ()


def app_role_credentials() -> tuple[str, str]:
    user = os.environ.get("APP_DB_USER", "")
    password = os.environ.get("APP_DB_PASSWORD", "")
    if not user or not password:
        raise RuntimeError("APP_DB_USER·APP_DB_PASSWORD 가 필요하다 — 마이그레이션은 앱 롤 권한까지 정비한다")
    return user, password


def _execute_formatted(connection: Connection, template: str, **params: str) -> None:
    """식별자·리터럴을 PostgreSQL format() 으로 인용한 뒤 실행한다(DDL 은 바인드 파라미터를 받지 않는다).

    format() 의 가변 인자는 타입을 추론하지 못하므로 바인드 값은 `CAST(:x AS text)` 로 넘긴다.
    """
    statement = connection.execute(text(f"SELECT format({template})"), params).scalar_one()
    connection.execute(text(statement))


def ensure_app_role(connection: Connection, user: str, password: str) -> None:
    exists = connection.execute(text("SELECT 1 FROM pg_roles WHERE rolname = :user"), {"user": user}).first()
    if exists is None:
        _execute_formatted(
            connection,
            "'CREATE ROLE %I LOGIN PASSWORD %L', CAST(:user AS text), CAST(:password AS text)",
            user=user,
            password=password,
        )
    else:
        _execute_formatted(
            connection,
            "'ALTER ROLE %I LOGIN PASSWORD %L', CAST(:user AS text), CAST(:password AS text)",
            user=user,
            password=password,
        )

    _execute_formatted(
        connection, "'GRANT CONNECT ON DATABASE %I TO %I', current_database(), CAST(:user AS text)", user=user
    )
    _execute_formatted(connection, "'GRANT USAGE ON SCHEMA public TO %I', CAST(:user AS text)", user=user)
    _execute_formatted(
        connection,
        "'GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO %I', CAST(:user AS text)",
        user=user,
    )
    _execute_formatted(
        connection, "'GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO %I', CAST(:user AS text)", user=user
    )
    # 이 마이그레이션 계정이 앞으로 만들 객체에도 같은 권한
    _execute_formatted(
        connection,
        "'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO %I', CAST(:user AS text)",
        user=user,
    )
    _execute_formatted(
        connection,
        "'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO %I', CAST(:user AS text)",
        user=user,
    )
    # append-only 표 — 위에서 모든 표에 준 UPDATE · DELETE 를 거둔다. 앱은 더하기만 한다.
    # 그 표를 만드는 revision 전까지만 올린 DB(`alembic upgrade <이전 revision>`)에는 표가 없어 건너뛴다
    for table in APPEND_ONLY_TABLES:
        if connection.execute(text("SELECT to_regclass(:name)"), {"name": f"public.{table}"}).scalar_one() is None:
            continue
        _execute_formatted(
            connection,
            "'REVOKE UPDATE, DELETE ON TABLE %I FROM %I', CAST(:table AS text), CAST(:user AS text)",
            table=table,
            user=user,
        )
