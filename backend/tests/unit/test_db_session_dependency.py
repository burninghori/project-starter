"""요청 세션(`DbDep`)의 commit 이 실패하면 성공 응답이 나가지 않는다 — commit 이 응답 머리보다 먼저다.

실제 앱(미들웨어 · 오류 처리기)에 이 테스트만의 쓰기 라우트를 하나 더하고, 요청 세션의 정리(commit)가 실패하게 만든다.
DB 는 쓰지 않는다 — 요청 세션 자리에 commit 에서 실패하는 블록을 끼운다.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import DbDep
from app.domains.auth.deps import AuthUser
from app.main import create_app

WRITE_PATH = "/api/v1/_test/commit-fails"


@asynccontextmanager
async def _session_whose_commit_fails() -> AsyncIterator[object]:
    yield object()
    raise RuntimeError("commit failed")


async def _write(db: AsyncSession = DbDep) -> dict[str, bool]:
    return {"written": True}


def test_commit_failure_is_an_error_response_not_a_success(
    monkeypatch: pytest.MonkeyPatch, stub_auth: Callable[..., AuthUser]
) -> None:
    monkeypatch.setattr("app.db.deps.session_scope", _session_whose_commit_fails)
    app = create_app()
    app.add_api_route(WRITE_PATH, _write, methods=["POST"])

    with TestClient(app, raise_server_exceptions=False) as client:
        stub_auth(client)
        response = client.post(WRITE_PATH)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_failure"
    assert response.headers.get("x-request-id")
