"""인증 API 왕복(로그인, 잘못된 자격, 비활성, 버전 회수, 게이트, 쿠키 재발급)."""

from collections.abc import Callable
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domains.auth.passwords import MAX_BYTES, generate_temp_password
from app.domains.auth.tokens import SESSION_COOKIE
from tests.plugins.auth import execute_sql

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
PASSWORD = "/api/v1/auth/password"
DOCS = "/api/docs"

MakeUser = Callable[..., tuple[str, str]]
LoginAs = Callable[[str, str], TestClient]


def test_login_roundtrip(db_client: TestClient, make_user: MakeUser) -> None:
    login_id, password = make_user(must_change_password=False)

    response = db_client.post(LOGIN, json={"loginId": login_id, "password": password})

    assert response.status_code == 200
    user = response.json()["user"]
    assert user["loginId"] == login_id
    assert user["role"] == "admin"
    assert user["mustChangePassword"] is False
    assert user["defaultPage"] == "/"
    cookie = response.headers["set-cookie"].lower()
    assert cookie.startswith(f"{SESSION_COOKIE}=") and "httponly" in cookie and "path=/api" in cookie
    assert db_client.get(ME).json()["user"] == user


def test_wrong_password_unknown_id_and_over_long_password_are_the_same_401(
    db_client: TestClient, make_user: MakeUser
) -> None:
    login_id, password = make_user(must_change_password=False)

    responses = [
        db_client.post(LOGIN, json={"loginId": login_id, "password": password + "x"}),
        db_client.post(LOGIN, json={"loginId": f"nobody-{uuid4().hex[:8]}", "password": password}),
        db_client.post(LOGIN, json={"loginId": login_id, "password": "a" * (MAX_BYTES + 1)}),
    ]

    for response in responses:
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "auth_invalid_credentials"
        # 아이디 없음과 비밀번호 틀림을 응답 본문으로도 구분하지 않는다
        assert "details" not in error and "message" not in error["diagnostic"]


def test_inactive_user_is_403(db_client: TestClient, make_user: MakeUser) -> None:
    login_id, password = make_user(must_change_password=False)
    execute_sql("UPDATE app_user SET is_active = false WHERE login_id = :login_id", login_id=login_id)

    response = db_client.post(LOGIN, json={"loginId": login_id, "password": password})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "auth_user_inactive"


def test_without_session_everything_but_health_and_login_is_401(db_client: TestClient) -> None:
    assert db_client.get(ME).json()["error"]["code"] == "auth_required"
    assert db_client.get(DOCS).status_code == 401
    assert db_client.get("/api/health").status_code == 200
    assert db_client.get("/api/health/ready").status_code == 200


def test_token_version_bump_revokes_existing_cookie(make_user: MakeUser, login_as: LoginAs) -> None:
    login_id, password = make_user(must_change_password=False)
    client = login_as(login_id, password)
    assert client.get(ME).status_code == 200

    execute_sql("UPDATE app_user SET token_version = token_version + 1 WHERE login_id = :login_id", login_id=login_id)

    assert client.get(ME).json()["error"]["code"] == "auth_required"


def test_password_change_gate_then_change_reissues_cookie(make_user: MakeUser, login_as: LoginAs) -> None:
    login_id, password = make_user(must_change_password=True)
    client = login_as(login_id, password)
    old_cookie = client.cookies.get(SESSION_COOKIE)
    assert old_cookie

    assert client.get(ME).json()["user"]["mustChangePassword"] is True
    blocked = client.get(DOCS)
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "auth_password_change_required"

    new_password = generate_temp_password()
    changed = client.post(PASSWORD, json={"currentPassword": password, "newPassword": new_password})
    assert changed.status_code == 200
    assert changed.json()["user"]["mustChangePassword"] is False
    assert client.cookies.get(SESSION_COOKIE) != old_cookie
    assert client.get(DOCS).status_code == 200

    # 옛 쿠키는 버전이 달라 더 쓸 수 없고, 새 비밀번호로는 다시 로그인된다
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, old_cookie)
    assert client.get(ME).json()["error"]["code"] == "auth_required"
    assert login_as(login_id, new_password).get(ME).status_code == 200


def test_password_change_rejects_wrong_current_and_rule_violations(make_user: MakeUser, login_as: LoginAs) -> None:
    login_id, password = make_user(must_change_password=False)
    client = login_as(login_id, password)

    wrong_current = client.post(PASSWORD, json={"currentPassword": password + "x", "newPassword": "valid-new-pw"})
    # 세션은 그대로 유효하다 — 로그인 실패(401)가 아니라 입력 오류(422)이고, 이 요청 뒤에도 로그인 상태다
    assert wrong_current.status_code == 422
    assert wrong_current.json()["error"]["code"] == "auth_current_password_invalid"
    assert client.get(ME).status_code == 200

    too_short = client.post(PASSWORD, json={"currentPassword": password, "newPassword": "short"})
    assert too_short.status_code == 422
    assert too_short.json()["error"]["code"] == "auth_password_rule_violation"
    assert too_short.json()["error"]["details"] == {"rule": "too_short"}

    with_space = client.post(PASSWORD, json={"currentPassword": password, "newPassword": "has space here"})
    assert with_space.json()["error"]["details"] == {"rule": "whitespace"}

    # 아무것도 바뀌지 않았다 — 원래 비밀번호로 그대로 로그인된다
    assert login_as(login_id, password).get(ME).status_code == 200


def test_logout_ends_session(make_user: MakeUser, login_as: LoginAs) -> None:
    client = login_as(*make_user(must_change_password=False))

    response = client.post(LOGOUT)
    assert response.status_code == 204
    header = response.headers["set-cookie"].lower()
    assert header.startswith(f'{SESSION_COOKIE}=""') and "max-age=0" in header
    assert client.get(ME).json()["error"]["code"] == "auth_required"


def test_password_change_gate_still_allows_logout(make_user: MakeUser, login_as: LoginAs) -> None:
    client = login_as(*make_user(must_change_password=True))

    assert client.post(LOGOUT).status_code == 204


def test_auth_client_is_an_admin_without_gate(auth_client: TestClient) -> None:
    user = auth_client.get(ME).json()["user"]

    assert user["role"] == "admin"
    assert user["mustChangePassword"] is False
    assert auth_client.get(DOCS).status_code == 200
