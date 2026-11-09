"""사용자 관리 API — 관리자 전용, 생성 · 수정 · 초기화의 세션 · 잠금 효과, 자기 자신 보호."""

import logging
from collections.abc import Callable
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from tests.plugins.auth import execute_sql, login

USERS = "/api/v1/users"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

MakeUser = Callable[..., tuple[str, str]]


def _new_login_id() -> str:
    return f"m-{uuid4().hex[:10]}"


def _create(client: TestClient, login_id: str, role: str = "member") -> dict:
    response = client.post(USERS, json={"loginId": login_id, "name": "홍길동", "org": "개발", "role": role})
    assert response.status_code == 201, response.text
    return response.json()


def test_non_admin_is_forbidden(db_client: TestClient, make_user: MakeUser) -> None:
    login(db_client, *make_user(must_change_password=False, role="member"))

    response = db_client.get(USERS, params={"page": 1})

    assert (response.status_code, response.json()["error"]["code"]) == (403, "auth_forbidden")


def test_create_issues_temp_password_once_and_gates_first_login(
    auth_client: TestClient, test_admin: tuple[str, str]
) -> None:
    login_id = _new_login_id()

    created = _create(auth_client, login_id)

    user = created["user"]
    assert (user["loginId"], user["role"], user["isActive"], user["mustChangePassword"]) == (
        login_id,
        "member",
        True,
        True,
    )
    assert user["lockedUntil"] is None
    listed = auth_client.get(USERS, params={"page": 1}).json()
    assert listed["total"] >= 1 and listed["pageCount"] >= 1
    assert auth_client.get(f"{USERS}/{user['id']}").json()["user"] == user

    login(auth_client, login_id, created["temporaryPassword"])
    assert auth_client.get(ME).json()["user"]["mustChangePassword"] is True


def test_duplicate_login_id_is_409(auth_client: TestClient) -> None:
    login_id = _new_login_id()
    _create(auth_client, login_id)

    response = auth_client.post(USERS, json={"loginId": login_id, "name": "다른", "org": "다른", "role": "member"})

    assert response.status_code == 409
    assert (response.json()["error"]["code"], response.json()["error"]["details"]) == (
        "user_login_id_taken",
        {"loginId": login_id},
    )


def test_deactivation_revokes_the_users_sessions(
    db_client: TestClient, make_user: MakeUser, test_admin: tuple[str, str]
) -> None:
    login_id, password = make_user(must_change_password=False, role="member")
    login(db_client, login_id, password)
    member_cookies = dict(db_client.cookies)
    member_id = db_client.get(ME).json()["user"]["id"]

    login(db_client, *test_admin)
    response = db_client.put(
        f"{USERS}/{member_id}", json={"name": "바뀐 이름", "org": "바뀐 소속", "role": "member", "isActive": False}
    )
    assert response.status_code == 200
    assert (response.json()["user"]["name"], response.json()["user"]["isActive"]) == ("바뀐 이름", False)

    db_client.cookies.clear()
    db_client.cookies.update(member_cookies)
    assert db_client.get(ME).json()["error"]["code"] == "auth_required"

    # 다시 사용하게 해도 옛 쿠키는 살아나지 않는다
    login(db_client, *test_admin)
    reactivate = {"name": "바뀐 이름", "org": "바뀐 소속", "role": "member", "isActive": True}
    assert db_client.put(f"{USERS}/{member_id}", json=reactivate).status_code == 200
    db_client.cookies.clear()
    db_client.cookies.update(member_cookies)
    assert db_client.get(ME).json()["error"]["code"] == "auth_required"


def test_put_requires_every_field(auth_client: TestClient) -> None:
    user_id = _create(auth_client, _new_login_id())["user"]["id"]

    response = auth_client.put(f"{USERS}/{user_id}", json={"name": "이름만"})

    assert (response.status_code, response.json()["error"]["code"]) == (422, "request_validation_failed")


def test_password_reset_revokes_sessions_and_unlocks(db_client: TestClient, test_admin: tuple[str, str]) -> None:
    login(db_client, *test_admin)
    created = _create(db_client, _new_login_id())
    login_id, user_id = created["user"]["loginId"], created["user"]["id"]

    login(db_client, login_id, created["temporaryPassword"])
    old_cookies = dict(db_client.cookies)
    execute_sql("UPDATE app_user SET locked_until = now() + interval '1 hour' WHERE id = :id", id=user_id)

    login(db_client, *test_admin)
    reset = db_client.post(f"{USERS}/{user_id}/password-reset")
    assert reset.status_code == 200
    assert reset.json()["user"]["lockedUntil"] is None
    new_password = reset.json()["temporaryPassword"]
    assert new_password != created["temporaryPassword"]

    db_client.cookies.clear()
    db_client.cookies.update(old_cookies)
    assert db_client.get(ME).json()["error"]["code"] == "auth_required"
    login(db_client, login_id, new_password)
    assert db_client.get(ME).status_code == 200


def test_admin_cannot_demote_deactivate_or_reset_self(auth_client: TestClient) -> None:
    me = auth_client.get(ME).json()["user"]
    body = {"name": me["name"], "org": "x", "role": "member", "isActive": True}

    demote = auth_client.put(f"{USERS}/{me['id']}", json=body)
    deactivate = auth_client.put(f"{USERS}/{me['id']}", json=body | {"role": me["role"], "isActive": False})
    reset = auth_client.post(f"{USERS}/{me['id']}/password-reset")

    for response in (demote, deactivate, reset):
        assert (response.status_code, response.json()["error"]["code"]) == (409, "user_self_change_forbidden")
    # 이름 · 소속은 바꿀 수 있다
    rename = auth_client.put(f"{USERS}/{me['id']}", json=body | {"role": me["role"]})
    assert rename.status_code == 200


def test_unknown_user_is_404_and_page_is_bounded(auth_client: TestClient) -> None:
    missing = auth_client.get(f"{USERS}/999999999")
    assert (missing.status_code, missing.json()["error"]["code"]) == (404, "resource_not_found")

    assert auth_client.get(USERS, params={"page": 0}).status_code == 422
    assert auth_client.get(USERS).status_code == 422


def test_lock_shows_in_user_detail(auth_client: TestClient, db_client: TestClient) -> None:
    created = _create(auth_client, _new_login_id())
    for _ in range(settings.login_max_failures):
        auth_client.post(LOGIN, json={"loginId": created["user"]["loginId"], "password": "wrong-password"})

    # 실패 요청은 쿠키를 건드리지 않는다 — 관리자 세션 그대로
    detail = auth_client.get(f"{USERS}/{created['user']['id']}").json()["user"]
    assert detail["lockedUntil"] is not None


def test_temporary_passwords_never_reach_the_logs(auth_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        created = _create(auth_client, _new_login_id())
        reset = auth_client.post(f"{USERS}/{created['user']['id']}/password-reset").json()

    logged = " ".join(str(record.__dict__) for record in caplog.records)
    for password in (created["temporaryPassword"], reset["temporaryPassword"]):
        assert password not in logged
