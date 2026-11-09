"""라우터가 쓰는 인증 의존성 — api.md 「인증 계약」의 이름 그대로.

- `CurrentUser`: 미들웨어(`app.middleware.auth`)가 쿠키 JWT → DB 대조까지 끝내고 scope state 에 둔 `AuthUser`.
- `RequireAdmin`: 관리자만. 아니면 403 `auth_forbidden`. 역할 값 목록은 프로젝트가 정하므로 **관리자 판별은 `is_admin` 한 곳**이다.

ORM 객체를 라우터에 넘기지 않는다 — `AuthUser` 는 요청 처리 동안 바뀌지 않는 스냅숏이다.
"""

from dataclasses import dataclass

from fastapi import Depends, Request

from ...api.error_contract import SemanticHTTPException
from .models import AppUser

# 관리자 역할 — 시드 관리자의 역할이고 `RequireAdmin` 이 보는 값이다. 역할 값 목록을 정하면 roles.py 로 옮긴다
ADMIN_ROLE = "admin"
# 미들웨어가 인증된 사용자를 두는 `scope["state"]` 키
AUTH_USER_STATE_KEY = "auth_user"


@dataclass(frozen=True, slots=True)
class AuthUser:
    id: int
    login_id: str
    name: str
    role: str
    must_change_password: bool
    # 로그인 직후 화면(`/auth/me` 응답에 싣는다)
    default_page: str
    # 쿠키와 대조가 끝난 현재 버전. 본인 비밀번호 변경의 기대 버전이다
    token_version: int

    @classmethod
    def from_row(cls, row: AppUser) -> "AuthUser":
        return cls(
            id=row.id,
            login_id=row.login_id,
            name=row.name,
            role=row.role,
            must_change_password=row.must_change_password,
            default_page=row.default_page,
            token_version=row.token_version,
        )


def is_admin(user: AuthUser) -> bool:
    """관리자 판별의 유일한 자리."""
    return user.role == ADMIN_ROLE


def _current_user(request: Request) -> AuthUser:
    user = request.scope.get("state", {}).get(AUTH_USER_STATE_KEY)
    if not isinstance(user, AuthUser):
        # 미들웨어가 제외한 경로(헬스체크·로그인)의 핸들러가 CurrentUser 를 쓰면 여기로 온다
        raise SemanticHTTPException(code="auth_required", diagnostic_message="no authenticated user on this request")
    return user


CurrentUser = Depends(_current_user)


def _require_admin(user: AuthUser = CurrentUser) -> AuthUser:
    if not is_admin(user):
        raise SemanticHTTPException(code="auth_forbidden", details={"required": ADMIN_ROLE})
    return user


RequireAdmin = Depends(_require_admin)
