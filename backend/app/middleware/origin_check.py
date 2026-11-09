"""쓰기 요청의 출처 검사 — CSRF 방어(결정 0006 「CSRF」, api.md 「인증 계약」).

세션 쿠키는 SameSite=Lax 라 다른 사이트의 폼 · fetch 에는 실리지 않지만, 같은 사이트(서브도메인 · 같은 등록 도메인의 다른 앱)에서
온 요청에는 실린다. 그래서 상태를 바꾸는 메서드는 브라우저가 붙이는 `Origin` 헤더를 `ALLOWED_ORIGINS` 와 대조한다.

- 대상: `/api` 아래의 GET · HEAD · OPTIONS 가 아닌 요청. 조회는 상태를 바꾸지 않는다는 규약이 전제다.
- `Origin` 이 목록 밖이거나 `null`(sandbox iframe · 파일 등) → 403 `request_origin_forbidden`.
- `Origin` 이 없으면 통과한다. 브라우저는 쓰기 요청에 언제나 `Origin` 을 붙이므로, 없는 요청은 브라우저가 아니다(명령 · 테스트 클라이언트) —
  남의 쿠키를 자동으로 싣는 주체가 아니라 CSRF 대상이 아니다.
- 인증 미들웨어 바깥이다 — 로그인 요청(로그인 CSRF)도 막고, DB 를 보기 전에 끝낸다.

순수 ASGI 라 예외 처리기를 거치지 않는다 — 오류는 `semantic_error_response` 로 직접 보낸다.
"""

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from ..api.error_contract import semantic_error_response
from ..config import settings
from ..logging import get_logger

logger = get_logger("middleware.origin_check")

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
API_PREFIX = "/api/"


class OriginCheckMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in SAFE_METHODS or not scope["path"].startswith(API_PREFIX):
            await self.app(scope, receive, send)
            return

        origin = Headers(scope=scope).get("origin")
        if origin is not None and origin not in settings.allowed_origins:
            logger.warning(
                "request origin rejected", extra={"origin": origin, "method": scope["method"], "path": scope["path"]}
            )
            response = semantic_error_response(
                code="request_origin_forbidden",
                details={"origin": origin},
                diagnostic_message="Origin is not in ALLOWED_ORIGINS",
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
