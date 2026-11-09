"""사용자 테이블 — docs/specs/db-schema.md 「app_user」, 결정 0006.

`user` 는 PostgreSQL 예약어라 `app_user`. 역할 값 목록은 프로젝트가 정하므로 CHECK 를 두지 않는다 —
정하면 CHECK 와 역할→메뉴 표를 `roles.py` 에 둔다(api.md 「인증 계약」).
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IdPkMixin, TimestampMixin
from app.db.types import UtcDateTime


class AppUser(IdPkMixin, TimestampMixin, Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("token_version >= 0", name="token_version_non_negative"),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count_non_negative"),
        {"comment": "사용자 계정"},
    )

    login_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="로그인 아이디")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="이름")
    # 소속
    org: Mapped[str] = mapped_column(String(100), nullable=False, comment="소속")
    # 값 목록 미정 — 시드 관리자는 "admin"
    role: Mapped[str] = mapped_column(String(32), nullable=False, comment="역할(값 목록 미정, 시드 관리자 admin)")
    # 「중지」
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="사용 여부(false = 중지)")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="비밀번호 해시")
    # 쿠키 JWT 무효화 카운터. 매 요청 대조
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, comment="쿠키 JWT 무효화 카운터 — 매 요청 대조")
    # 관리자 초기화 후
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="다음 로그인에 비밀번호 변경 필요(관리자 초기화 뒤)"
    )
    # 잠금 전 연속 로그인 실패 횟수. 성공 · 잠금 · 관리자 초기화 때 0
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="연속 로그인 실패 횟수 — 성공 · 잠금 · 관리자 초기화 때 0"
    )
    # 이 시각 전까지 로그인을 받지 않는다. 잠긴 적 없거나 풀렸으면 null 또는 지난 시각
    locked_until: Mapped[datetime | None] = mapped_column(
        UtcDateTime, nullable=True, comment="로그인 잠금이 풀리는 시각(null = 잠금 없음)"
    )
    # 로그인 직후 화면
    default_page: Mapped[str] = mapped_column(String(32), nullable=False, comment="로그인 직후 화면의 경로")
