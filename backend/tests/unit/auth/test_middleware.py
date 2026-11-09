"""인증 미들웨어 — 제외 경로, 401/403 응답, 게이트, 로그아웃. DB 대조는 `stub_auth` 가 고정한다."""

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.domains.auth.deps import AuthUser
from app.domains.auth.tokens import SESSION_COOKIE, issue_token

ME = "/api/v1/auth/me"
LOGIN = "/api/v1/auth/login"
DOCS = "/api/docs"


def test_missing_cookie_is_401_with_envelope_and_request_id(client: TestClient) -> None:
    response = client.get(ME)

    assert response.status_code == 401
    error = response.json()["error"]
    assert (error["contract"], error["family"], error["code"]) == ("semantic-v1", "authentication", "auth_required")
    # 인증 미들웨어가 request_context 안쪽이라 request_id 가 붙는다
    assert error["diagnostic"]["requestId"] == response.headers["x-request-id"]
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_garbage_cookie_is_401(client: TestClient) -> None:
    client.cookies.set(SESSION_COOKIE, "not-a-token")

    assert client.get(ME).json()["error"]["code"] == "auth_required"


def test_login_path_is_open(client: TestClient) -> None:
    # 인증 벽이 아니라 요청 검증(422)까지 간다
    assert client.post(LOGIN, json={}).status_code == 422


def test_api_docs_need_login(client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    assert client.get(DOCS).status_code == 401

    stub_auth(client)
    assert client.get(DOCS).status_code == 200


def test_me_returns_user_envelope(client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    user = stub_auth(client)

    response = client.get(ME)

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "id": user.id,
            "loginId": user.login_id,
            "name": user.name,
            "role": "admin",
            "mustChangePassword": False,
            "defaultPage": "/",
        }
    }


def test_token_version_mismatch_is_401(client: TestClient, stub_auth: Callable[..., AuthUser]) -> None:
    user = stub_auth(client)
    client.cookies.set(SESSION_COOKIE, issue_token(user.id, user.token_version + 1))

    assert client.get(ME).json()["error"]["code"] == "auth_required"


def test_password_change_gate_blocks_everything_but_auth_paths(
    client: TestClient, stub_auth: Callable[..., AuthUser]
) -> None:
    stub_auth(client, must_change_password=True)

    assert client.get(ME).status_code == 200
    blocked = client.get(DOCS)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "auth_password_change_required"
    # 게이트 안에서도 로그아웃은 열려 있다
    assert client.post("/api/v1/auth/logout").status_code == 204
