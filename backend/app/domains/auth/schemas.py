"""인증 · 사용자 관리 API 입출력 모델(api.md 「인증」 · 「사용자 관리」)."""

from datetime import datetime

from pydantic import Field

from ...api.schemas import ApiBase, ApiRequestBase


class LoginIn(ApiRequestBase):
    login_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class PasswordChangeIn(ApiRequestBase):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class AuthUserOut(ApiBase):
    id: int
    login_id: str
    name: str
    role: str
    must_change_password: bool
    # 로그인 직후 화면의 경로. 화면은 이 경로로 그대로 간다 — 등록되지 않은 경로를 대체하지 않는다
    default_page: str


class AuthUserEnvelope(ApiBase):
    """로그인 · `/auth/me` · 비밀번호 변경이 같은 모양으로 답한다."""

    user: AuthUserOut


# ---------- 사용자 관리(관리자) ----------
# 칸 길이는 app_user 컬럼과 같다 — 넘는 값은 DB 오류(500)가 아니라 경계의 422 다


class UserCreateIn(ApiRequestBase):
    login_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    org: str = Field(min_length=1, max_length=100)
    # 역할 값 목록은 프로젝트가 정한다 — 정하면 Literal 로 좁힌다
    role: str = Field(min_length=1, max_length=32)


class UserUpdateIn(ApiRequestBase):
    """전체 교체(PUT) — 칸을 모두 보낸다. 빠진 칸을 「그대로 둠」으로 읽지 않는다."""

    name: str = Field(min_length=1, max_length=100)
    org: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=32)
    is_active: bool


class UserOut(ApiBase):
    id: int
    login_id: str
    name: str
    org: str
    role: str
    is_active: bool
    must_change_password: bool
    # 잠금이 풀리는 시각. 잠긴 적 없으면 null — 지난 시각이면 이미 풀린 것이다
    locked_until: datetime | None
    created_at: datetime
    updated_at: datetime


class UserEnvelope(ApiBase):
    user: UserOut


class UserWithTempPasswordOut(ApiBase):
    """생성 · 비밀번호 초기화 응답. 임시 비밀번호는 이 응답에서 한 번만 보이고 서버는 해시만 둔다."""

    user: UserOut
    temporary_password: str
