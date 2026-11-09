"""쓰기 요청의 출처 검사(CSRF 방어) — DB 없이 미들웨어 순서와 판정을 본다.

로그인 본문을 비워 보내면 출처 검사를 통과한 요청은 DB 를 보기 전에 422 로 끝난다 — 통과 여부를 그것으로 구분한다.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
ALLOWED = next(iter(settings.allowed_origins))


@pytest.mark.parametrize("origin", ["https://evil.example.com", "null", f"{ALLOWED}.evil.example.com", f"{ALLOWED}/"])
def test_write_from_an_unlisted_origin_is_403_before_login(client: TestClient, origin: str) -> None:
    response = client.post(LOGIN, json={}, headers={"Origin": origin})

    assert response.status_code == 403
    error = response.json()["error"]
    assert (error["code"], error["details"]) == ("request_origin_forbidden", {"origin": origin})
    assert response.headers["x-request-id"]


def test_origin_is_checked_before_authentication(client: TestClient) -> None:
    response = client.post(ME, headers={"Origin": "https://evil.example.com"})

    assert response.json()["error"]["code"] == "request_origin_forbidden"


def test_listed_or_missing_origin_passes_through(client: TestClient) -> None:
    listed = client.post(LOGIN, json={}, headers={"Origin": ALLOWED})
    missing = client.post(LOGIN, json={})

    for response in (listed, missing):
        assert response.json()["error"]["code"] == "request_validation_failed"


def test_reads_are_not_checked(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "https://evil.example.com"})

    assert response.status_code == 200


@pytest.mark.parametrize("value", ["", " , ", "http://localhost:5174/", "localhost:5174", "http://a.example.com/path"])
def test_allowed_origins_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, allowed_origins=value)  # pyright: ignore[reportCallIssue]


def test_allowed_origins_splits_on_commas() -> None:
    parsed = Settings(_env_file=None, allowed_origins="https://a.example.com, http://localhost:5174")  # pyright: ignore[reportCallIssue]

    assert parsed.allowed_origins == frozenset({"https://a.example.com", "http://localhost:5174"})
