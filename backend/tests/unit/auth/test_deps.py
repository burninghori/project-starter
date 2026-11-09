"""라우터 의존성 `CurrentUser` · `RequireAdmin` — api.md 「인증 계약」."""

from collections.abc import Callable, Iterator

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.domains.auth.deps import AuthUser, CurrentUser, RequireAdmin
from app.main import create_app

router = APIRouter(prefix="/api/v1/_auth_test")


@router.get("/me")
async def me(user: AuthUser = CurrentUser) -> dict[str, str]:
    return {"loginId": user.login_id}


@router.get("/admin")
async def admin_only(user: AuthUser = RequireAdmin) -> dict[str, str]:
    return {"loginId": user.login_id}


@pytest.fixture
def test_client() -> Iterator[TestClient]:
    app = create_app()
    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_current_user_is_the_authenticated_user(test_client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    user = stub_auth(test_client)

    assert test_client.get("/api/v1/_auth_test/me").json() == {"loginId": user.login_id}


def test_admin_only(test_client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    stub_auth(test_client, role="member")
    forbidden = test_client.get("/api/v1/_auth_test/admin")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["details"] == {"required": "admin"}

    stub_auth(test_client, role="admin")
    assert test_client.get("/api/v1/_auth_test/admin").status_code == 200
