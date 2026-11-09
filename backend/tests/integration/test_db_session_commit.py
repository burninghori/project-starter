"""요청 세션(`DbDep`)의 commit 시점 — 쓰기 API 는 commit 을 마친 뒤에 응답 머리를 보낸다.

테스트 클라이언트는 앱이 정리(commit)까지 끝낸 뒤에 응답을 돌려주므로, commit 이 응답보다 늦어도 보통의 왕복으로는 보이지 않는다.
그래서 앱을 감싸 응답 머리(`http.response.start`)가 나가는 순간에 다른 DB 접속으로 방금 쓴 값을 읽는다.
쓰기 API 는 비밀번호 변경(`token_version` 을 올린다)을 쓴다 — 테스트마다 새 사용자라 다른 테스트에 남는 것이 없다.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from starlette.types import Message, Receive, Scope, Send

from app.db.engine import database_url
from app.main import create_app
from tests.plugins.auth import login

PASSWORD = "/api/v1/auth/password"
NEW_PASSWORD = "new-pass-1234"


async def _token_version_elsewhere(login_id: str) -> int:
    """앱의 요청 세션이 아닌 접속에서 읽는다 — 커밋된 값만 보인다(조회만 해 앱의 트랜잭션을 기다리지 않는다)."""
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text("SELECT token_version FROM app_user WHERE login_id = :login_id"), {"login_id": login_id}
            )
            return result.scalar_one()
    finally:
        await engine.dispose()


def test_write_is_committed_before_the_response_starts(
    migrated_database: str, make_user: Callable[..., tuple[str, str]]
) -> None:
    login_id, password = make_user(must_change_password=False)
    versions_at_response_start: list[int] = []
    app = create_app()

    async def probing_app(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or (scope["method"], scope["path"]) != ("POST", PASSWORD):
            await app(scope, receive, send)
            return

        async def send_probing(message: Message) -> None:
            if message["type"] == "http.response.start":
                versions_at_response_start.append(await _token_version_elsewhere(login_id))
            await send(message)

        await app(scope, receive, send_probing)

    with TestClient(probing_app, raise_server_exceptions=False) as client:
        login(client, login_id, password)
        changed = client.post(PASSWORD, json={"currentPassword": password, "newPassword": NEW_PASSWORD})

        assert changed.status_code == 200, changed.text
        assert versions_at_response_start == [1]
