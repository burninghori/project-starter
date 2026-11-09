"""계정 명령 2개(관리자 시드 · 비밀번호 초기화). 명령은 자기 엔진을 세우므로 앱 클라이언트를 연 채로 돌리지 않는다."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.domains.auth import reset_password, seed_admin
from app.domains.auth.tokens import SESSION_COOKIE
from app.main import create_app

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
DOCS = "/api/docs"


@contextmanager
def api() -> Iterator[TestClient]:
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


def _temp_password_from(stdout: str) -> str:
    lines = [line for line in stdout.splitlines() if line.startswith("임시 비밀번호")]
    assert len(lines) == 1, stdout
    return lines[0].split(": ", 1)[1].strip()


def test_seed_admin_creates_once(
    migrated_database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    login_id = f"seed-{uuid4().hex[:8]}"
    monkeypatch.setenv("ADMIN_LOGIN_ID", login_id)
    monkeypatch.setenv("ADMIN_INITIAL_PASSWORD", "change-me-now")

    assert seed_admin.main() == 0
    assert "만들었다" in capsys.readouterr().out
    assert seed_admin.main() == 0
    assert "이미 있다" in capsys.readouterr().out

    with api() as client:
        response = client.post(LOGIN, json={"loginId": login_id, "password": "change-me-now"})
        assert response.status_code == 200
        user = response.json()["user"]
        assert (user["role"], user["mustChangePassword"]) == ("admin", True)
        assert client.get(DOCS).json()["error"]["code"] == "auth_password_change_required"


def test_seed_admin_rejects_initial_password_against_rules(
    migrated_database: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    login_id = f"seed-{uuid4().hex[:8]}"
    monkeypatch.setenv("ADMIN_LOGIN_ID", login_id)
    monkeypatch.setenv("ADMIN_INITIAL_PASSWORD", "pw-1234")

    assert seed_admin.main() == 1
    err = capsys.readouterr().err
    # 사유만 알리고 값은 출력하지 않는다
    assert "too_short" in err and "pw-1234" not in err

    # 계정은 만들어지지 않았다
    with api() as client:
        response = client.post(LOGIN, json={"loginId": login_id, "password": "pw-1234"})
        assert response.json()["error"]["code"] == "auth_invalid_credentials"


def test_reset_password_revokes_sessions_and_gates(
    make_user: Callable[..., tuple[str, str]], capsys: pytest.CaptureFixture[str]
) -> None:
    login_id, password = make_user(must_change_password=False)
    with api() as client:
        assert client.post(LOGIN, json={"loginId": login_id, "password": password}).status_code == 200
        old_cookie = client.cookies.get(SESSION_COOKIE)
    assert old_cookie

    assert reset_password.main(["--login-id", login_id]) == 0
    new_password = _temp_password_from(capsys.readouterr().out)

    with api() as client:
        client.cookies.set(SESSION_COOKIE, old_cookie)
        assert client.get(ME).json()["error"]["code"] == "auth_required"
        client.cookies.clear()
        assert client.post(LOGIN, json={"loginId": login_id, "password": password}).status_code == 401
        response = client.post(LOGIN, json={"loginId": login_id, "password": new_password})
        assert response.status_code == 200
        assert response.json()["user"]["mustChangePassword"] is True
        assert client.get(DOCS).json()["error"]["code"] == "auth_password_change_required"


def test_reset_password_unknown_login_id_fails(migrated_database: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert reset_password.main(["--login-id", f"nobody-{uuid4().hex[:8]}"]) == 1
    assert "없는 아이디" in capsys.readouterr().err
