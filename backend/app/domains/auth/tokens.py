"""세션 토큰(JWT HS256)과 세션 쿠키의 단일 출처(결정 0006, api.md 「인증」).

토큰에는 사용자 ID(`sub`)와 발급 시점의 `token_version`(`tv`)만 싣는다. 역할·권한은 넣지 않는다 — 매 요청
미들웨어가 DB 행을 읽어 대조한다. 리프레시 토큰은 없다.

쿠키는 httpOnly · SameSite=Lax · Path=/api 이고 Secure 는 `COOKIE_SECURE`, 만료는 `JWT_TTL_MINUTES` 다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from starlette.requests import Request
from starlette.responses import Response

from ...config import settings
from ...logging import get_logger

logger = get_logger("domains.auth.tokens")

SESSION_COOKIE = "app_session"
# frontend 개발 서버와 CloudFront 모두 /api 아래를 backend 로 보낸다. 쿠키도 그 범위에만 붙는다
COOKIE_PATH = "/api"
JWT_ALGORITHM = "HS256"


@dataclass(frozen=True, slots=True)
class SessionClaims:
    user_id: int
    token_version: int


def issue_token(user_id: int, token_version: int) -> str:
    issued_at = datetime.now(UTC)
    payload = {
        # PyJWT 는 sub 가 문자열이어야 해석한다
        "sub": str(user_id),
        "tv": token_version,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.jwt_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> SessionClaims | None:
    """서명·만료·필수 claim 이 맞으면 claims, 아니면 None. 사유는 debug 로 남긴다(정상 흐름의 예상 실패)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "tv", "iat", "exp"]},
        )
        return SessionClaims(user_id=int(payload["sub"]), token_version=int(payload["tv"]))
    except (jwt.InvalidTokenError, TypeError, ValueError) as exc:
        logger.debug("session token rejected", extra={"reason": f"{type(exc).__name__}: {exc}"})
        return None


def read_session_token(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.jwt_ttl_minutes * 60,
        path=COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path=COOKIE_PATH,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
