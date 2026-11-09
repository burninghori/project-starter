"""쿠키 JWT 를 검증하고 DB 사용자 행과 대조하는 ASGI 미들웨어(결정 0006, api.md 「인증 계약」).

- 제외 경로는 헬스체크와 로그인뿐이다. 그 밖의 모든 요청(API 문서 포함)은 세션 쿠키가 있어야 한다.
- 쿠키 없음·해석 실패·사용자 없음·버전 불일치 → 401 `auth_required`(쿠키 삭제 헤더 포함),
  비활성 → 403 `auth_user_inactive`, `must_change_password` 인데 허용 경로 밖 → 403 `auth_password_change_required`.
- 통과한 사용자는 `scope["state"]["auth_user"]` 에 두고 라우터는 `CurrentUser` 로 꺼낸다.

순수 ASGI 라 예외 처리기를 거치지 않는다 — 오류는 `semantic_error_response_for` 로 직접 보낸다(raise 하면 500).
`RequestContextMiddleware` 안쪽에 두어 request_id 와 접근 로그가 이 응답에도 붙는다(main.py 의 등록 순서).
"""

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from ..api.error_contract import SemanticHTTPException, semantic_error_response_for
from ..db.engine import session_scope
from ..domains.auth.deps import AUTH_USER_STATE_KEY, AuthUser
from ..domains.auth.service import resolve_session
from ..domains.auth.tokens import clear_session_cookie, decode_token, read_session_token

# 로그인 전에도 열려 있는 경로. 정확히 이 경로만이다(접두어 매칭 없음)
EXEMPT_PATHS = frozenset({"/api/health", "/api/health/ready", "/api/v1/auth/login"})
# 비밀번호를 바꿔야 하는 사용자에게 열린 경로
PASSWORD_GATE_ALLOWED_PATHS = frozenset({"/api/v1/auth/me", "/api/v1/auth/logout", "/api/v1/auth/password"})


class AuthMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        try:
            user = await _authenticate(scope)
        except SemanticHTTPException as exc:
            response = semantic_error_response_for(exc)
            if exc.status_code == 401:
                # 더 쓸 수 없는 쿠키는 지워 준다 — 다음 요청이 같은 401 을 반복하지 않는다
                clear_session_cookie(response)
            await response(scope, receive, send)
            return

        scope.setdefault("state", {})[AUTH_USER_STATE_KEY] = user
        await self.app(scope, receive, send)


async def _authenticate(scope: Scope) -> AuthUser:
    token = read_session_token(Request(scope))
    if token is None:
        raise SemanticHTTPException(code="auth_required", diagnostic_message="session cookie missing")
    claims = decode_token(token)
    if claims is None:
        raise SemanticHTTPException(code="auth_required", diagnostic_message="session token invalid or expired")

    async with session_scope() as db:
        user = await resolve_session(db, claims)

    if user.must_change_password and scope["path"] not in PASSWORD_GATE_ALLOWED_PATHS:
        raise SemanticHTTPException(code="auth_password_change_required")
    return user
