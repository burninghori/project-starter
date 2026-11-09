"""인증 테스트 fixture — api.md 「인증 계약」의 `auth_client`·`login_as`, 그리고 DB 없는 unit 용 `stub_auth`.

unit(DB 없음):
- `stub_auth(client, **overrides) -> AuthUser`: 미들웨어의 DB 대조(`resolve_session`)를 고정 사용자로 바꾸고
  그 사용자의 유효한 세션 쿠키를 `client` 에 넣는다. 쿠키 해석·게이트·권한 의존성은 실제 코드가 돈다.

integration(마이그레이션된 테스트 DB):
- `make_user(must_change_password=…, role=…) -> (login_id, password)`: 서비스 함수로 계정을 만든다(역할을 주지 않으면 admin).
- `auth_client`: 관리자(세션당 한 번 만든다, 게이트 없음)로 로그인된 `db_client`.
- `login_as(login_id, password) -> TestClient`: 지정 사용자로 로그인된 클라이언트.
  TestClient 하나가 세션 하나다 — DB 엔진이 클라이언트의 이벤트 루프에 묶여 두 번째 클라이언트를 열 수 없다.
  같은 테스트에서 다른 사용자로 바꾸면 이전 쿠키는 사라진다. 두 세션을 번갈아 쓰려면 `client.cookies` 값을 보관한다.
- `execute_sql(statement, **params)`: 테스트가 행을 직접 바꿀 때(비활성화·버전 올리기) — 자기 엔진으로 한 번 실행한다.
"""

import asyncio
from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.error_contract import SemanticHTTPException
from app.db.engine import database_url
from app.domains.auth.deps import ADMIN_ROLE, AuthUser
from app.domains.auth.passwords import generate_temp_password
from app.domains.auth.service import create_user
from app.domains.auth.tokens import SESSION_COOKIE, SessionClaims, issue_token

STUB_USER = AuthUser(
    id=1,
    login_id="stub",
    name="스텁 사용자",
    role="admin",
    must_change_password=False,
    default_page="/",
    token_version=0,
)

LOGIN_PATH = "/api/v1/auth/login"


@pytest.fixture
def stub_auth(monkeypatch: pytest.MonkeyPatch) -> Callable[..., AuthUser]:
    state = {"user": STUB_USER}

    async def resolve_session(_db: AsyncSession, claims: SessionClaims) -> AuthUser:
        user = state["user"]
        if claims.user_id != user.id or claims.token_version != user.token_version:
            raise SemanticHTTPException(code="auth_required", diagnostic_message="stub: claims mismatch")
        return user

    monkeypatch.setattr("app.middleware.auth.resolve_session", resolve_session)

    def as_user(client: TestClient, **overrides: Any) -> AuthUser:
        user = replace(STUB_USER, **overrides)
        state["user"] = user
        client.cookies.set(SESSION_COOKIE, issue_token(user.id, user.token_version))
        return user

    return as_user


async def _with_session(action: Callable[[AsyncSession], Any]) -> Any:
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            return await action(session)
    finally:
        await engine.dispose()


def execute_sql(statement: str, **params: Any) -> None:
    async def action(session: AsyncSession) -> None:
        await session.execute(text(statement), params)

    asyncio.run(_with_session(action))


def _create_user(login_id: str, password: str, must_change_password: bool, role: str) -> None:
    async def action(session: AsyncSession) -> None:
        await create_user(
            session,
            login_id=login_id,
            name=f"테스트 {login_id}",
            org="테스트",
            role=role,
            password=password,
            must_change_password=must_change_password,
        )

    asyncio.run(_with_session(action))


@pytest.fixture
def make_user(migrated_database: str) -> Callable[..., tuple[str, str]]:
    def _make(*, must_change_password: bool, login_id: str | None = None, role: str = ADMIN_ROLE) -> tuple[str, str]:
        resolved_id = login_id if login_id is not None else f"u-{uuid4().hex[:10]}"
        password = generate_temp_password()
        _create_user(resolved_id, password, must_change_password, role)
        return resolved_id, password

    return _make


def login(client: TestClient, login_id: str, password: str) -> TestClient:
    client.cookies.clear()
    response = client.post(LOGIN_PATH, json={"loginId": login_id, "password": password})
    if response.status_code != 200:
        raise RuntimeError(f"테스트 로그인 실패: {response.status_code} {response.text}")
    return client


@pytest.fixture(scope="session")
def test_admin(migrated_database: str) -> tuple[str, str]:
    login_id = f"admin-{uuid4().hex[:8]}"
    password = generate_temp_password()
    _create_user(login_id, password, must_change_password=False, role=ADMIN_ROLE)
    return login_id, password


@pytest.fixture
def auth_client(db_client: TestClient, test_admin: tuple[str, str]) -> TestClient:
    return login(db_client, *test_admin)


@pytest.fixture
def login_as(db_client: TestClient) -> Callable[[str, str], TestClient]:
    def _login_as(login_id: str, password: str) -> TestClient:
        return login(db_client, login_id, password)

    return _login_as
