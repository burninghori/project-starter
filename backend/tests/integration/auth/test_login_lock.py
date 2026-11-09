"""로그인 잠금 — 같은 계정의 연속 실패가 한도에 닿으면 잠그고, 잠긴 동안은 맞는 비밀번호도 받지 않는다(.env.test 의 한도)."""

import logging
from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from tests.plugins.auth import execute_sql

LOGIN = "/api/v1/auth/login"

MakeUser = Callable[..., tuple[str, str]]


def _fail(client: TestClient, login_id: str, times: int) -> list[int]:
    return [
        client.post(LOGIN, json={"loginId": login_id, "password": "wrong-password"}).status_code for _ in range(times)
    ]


def test_reaching_the_limit_locks_even_the_right_password(db_client: TestClient, make_user: MakeUser) -> None:
    login_id, password = make_user(must_change_password=False)
    limit = settings.login_max_failures

    statuses = _fail(db_client, login_id, limit)

    # 한도 전까지는 보통 실패, 한도에 닿는 실패부터 잠금
    assert statuses == [401] * (limit - 1) + [429]
    locked = db_client.post(LOGIN, json={"loginId": login_id, "password": password})
    assert locked.status_code == 429
    error = locked.json()["error"]
    assert (error["family"], error["code"]) == ("too_many_requests", "auth_login_locked")
    assert datetime.fromisoformat(error["details"]["lockedUntil"]) > datetime.now().astimezone()


def test_lock_expires_and_counting_starts_over(db_client: TestClient, make_user: MakeUser) -> None:
    login_id, password = make_user(must_change_password=False)
    _fail(db_client, login_id, settings.login_max_failures)
    execute_sql("UPDATE app_user SET locked_until = now() - interval '1 second' WHERE login_id = :id", id=login_id)

    assert db_client.post(LOGIN, json={"loginId": login_id, "password": password}).status_code == 200
    # 잠금이 풀린 뒤에는 처음부터 다시 센다
    assert _fail(db_client, login_id, settings.login_max_failures - 1) == [401] * (settings.login_max_failures - 1)


def test_success_resets_the_failure_count(db_client: TestClient, make_user: MakeUser) -> None:
    login_id, password = make_user(must_change_password=False)
    below_limit = settings.login_max_failures - 1

    _fail(db_client, login_id, below_limit)
    assert db_client.post(LOGIN, json={"loginId": login_id, "password": password}).status_code == 200

    assert _fail(db_client, login_id, below_limit) == [401] * below_limit


def test_unknown_login_id_is_never_locked(db_client: TestClient) -> None:
    assert set(_fail(db_client, "nobody-at-all", settings.login_max_failures + 1)) == {401}


def test_rejections_are_logged_as_warnings_without_the_password(
    db_client: TestClient, make_user: MakeUser, caplog: pytest.LogCaptureFixture
) -> None:
    login_id, _ = make_user(must_change_password=False)

    with caplog.at_level(logging.WARNING, logger="app.domains.auth"):
        _fail(db_client, login_id, settings.login_max_failures)

    records = [r for r in caplog.records if r.name == "app.domains.auth" and r.levelno >= logging.WARNING]
    assert [r.getMessage() for r in records] == ["login rejected"] * (settings.login_max_failures - 1) + [
        "login locked"
    ]
    assert all("wrong-password" not in str(r.__dict__) for r in records)


def test_inactive_account_still_counts_failures(db_client: TestClient, make_user: MakeUser) -> None:
    # 비밀번호를 먼저 본다 — 사용 중지 계정도 대입은 세고 잠근다. 맞는 비밀번호일 때만 「사용 중지」를 알려 준다
    login_id, password = make_user(must_change_password=False)
    execute_sql("UPDATE app_user SET is_active = false WHERE login_id = :id", id=login_id)

    assert db_client.post(LOGIN, json={"loginId": login_id, "password": password}).status_code == 403
    assert _fail(db_client, login_id, settings.login_max_failures)[-1] == 429
