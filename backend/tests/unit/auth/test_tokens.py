"""세션 토큰(JWT)과 쿠키 속성 — api.md 「인증」의 쿠키 계약."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from starlette.responses import Response

from app.config import settings
from app.domains.auth.tokens import (
    COOKIE_PATH,
    JWT_ALGORITHM,
    SESSION_COOKIE,
    SessionClaims,
    clear_session_cookie,
    decode_token,
    issue_token,
    set_session_cookie,
)


def _encode(payload: dict[str, Any], secret: str = settings.jwt_secret.get_secret_value()) -> str:
    return jwt.encode(payload, secret, algorithm=JWT_ALGORITHM)


def _fresh(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    return {"sub": "7", "tv": 3, "iat": now, "exp": now + timedelta(hours=1), **overrides}


def test_issue_and_decode_roundtrip() -> None:
    assert decode_token(issue_token(7, 3)) == SessionClaims(user_id=7, token_version=3)


def test_other_secret_is_rejected() -> None:
    assert decode_token(_encode(_fresh(), secret="someone-else")) is None


def test_expired_token_is_rejected() -> None:
    past = datetime.now(UTC) - timedelta(hours=2)
    assert decode_token(_encode(_fresh(iat=past, exp=past + timedelta(minutes=1)))) is None


def test_missing_claim_is_rejected() -> None:
    payload = _fresh()
    del payload["tv"]
    assert decode_token(_encode(payload)) is None


def test_non_numeric_subject_is_rejected() -> None:
    assert decode_token(_encode(_fresh(sub="not-a-number"))) is None


def test_session_cookie_attributes() -> None:
    response = Response()
    set_session_cookie(response, "token-value")
    header = response.headers["set-cookie"].lower()

    assert header.startswith(f"{SESSION_COOKIE}=token-value")
    assert "httponly" in header
    assert "samesite=lax" in header
    assert f"path={COOKIE_PATH}" in header
    assert f"max-age={settings.jwt_ttl_minutes * 60}" in header
    # .env.test 는 COOKIE_SECURE=false — 로컬 http 에서도 쿠키가 붙어야 한다
    assert "secure" not in header


def test_clear_cookie_expires_immediately() -> None:
    response = Response()
    clear_session_cookie(response)
    header = response.headers["set-cookie"].lower()

    assert header.startswith(f'{SESSION_COOKIE}=""')
    assert "max-age=0" in header
    assert f"path={COOKIE_PATH}" in header
