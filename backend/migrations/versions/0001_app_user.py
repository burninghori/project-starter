"""사용자 계정 테이블(app_user)과 테이블 · 컬럼 설명

테이블 정의는 docs/specs/db-schema.md 「app_user」, 결정 0006. 관리자 계정은 명령(app.domains.auth.seed_admin)이 만든다.

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""

import sqlalchemy as sa
from alembic import op
from migrations.forward_only import downgrade_not_supported

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False, comment="행 번호(PK, 자동 증가)"),
        sa.Column("login_id", sa.String(length=64), nullable=False, comment="로그인 아이디"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="이름"),
        sa.Column("org", sa.String(length=100), nullable=False, comment="소속"),
        sa.Column("role", sa.String(length=32), nullable=False, comment="역할(값 목록 미정, 시드 관리자 admin)"),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="사용 여부(false = 중지)"),
        sa.Column("password_hash", sa.String(length=255), nullable=False, comment="비밀번호 해시"),
        sa.Column("token_version", sa.Integer(), nullable=False, comment="쿠키 JWT 무효화 카운터 — 매 요청 대조"),
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            comment="다음 로그인에 비밀번호 변경 필요(관리자 초기화 뒤)",
        ),
        sa.Column(
            "failed_login_count",
            sa.Integer(),
            nullable=False,
            comment="연속 로그인 실패 횟수 — 성공 · 잠금 · 관리자 초기화 때 0",
        ),
        sa.Column(
            "locked_until",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="로그인 잠금이 풀리는 시각(null = 잠금 없음)",
        ),
        sa.Column("default_page", sa.String(length=32), nullable=False, comment="로그인 직후 화면의 경로"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="행을 만든 시각",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="행을 마지막으로 고친 시각",
        ),
        sa.CheckConstraint("token_version >= 0", name=op.f("ck_app_user_token_version_non_negative")),
        sa.CheckConstraint("failed_login_count >= 0", name=op.f("ck_app_user_failed_login_count_non_negative")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_app_user")),
        sa.UniqueConstraint("login_id", name=op.f("uq_app_user_login_id")),
        comment="사용자 계정",
    )


def downgrade() -> None:
    downgrade_not_supported()
