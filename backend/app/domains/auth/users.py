"""사용자 관리 서비스 — 관리자가 계정을 보고 · 만들고 · 고치고 · 비밀번호를 초기화한다(api.md 「사용자 관리」).

- 계정을 지우는 경로는 없다. 그만 쓰는 계정은 사용 중지(`is_active=false`)한다 — 다른 테이블의 사람 칸이 FK 로 가리킨다.
- 사용 중지는 `token_version` 을 무조건 올려 그 계정의 쿠키를 모두 무효로 한다(결정 0006) — 다시 사용하게 해도 옛 쿠키는 살아나지 않는다.
  역할 변경은 다음 요청부터 먹는다. 미들웨어가 매 요청 DB 행을 읽기 때문이다.
- 관리자는 자기 역할 · 사용 여부를 바꾸거나 자기 비밀번호를 초기화하지 않는다(409 `user_self_change_forbidden`).
  자기 비밀번호는 `/auth/password` 로 바꾼다.
- 활성 관리자는 늘 한 명 이상 남는다(409 `user_last_admin_required`). 관리자를 강등 · 사용 중지하는 변경은 활성 관리자 행을 id 순으로
  잠그고 센다 — 두 관리자가 동시에 서로를 강등해도 뒤에 온 쪽이 앞의 commit 을 보고 거절된다. 관리자가 0명이 되면 앱 안에서
  되돌릴 길이 없다(명령 `reset_password` 는 역할을 바꾸지 않는다).
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.error_contract import SemanticHTTPException
from ...logging import get_logger
from . import service
from .deps import ADMIN_ROLE, AuthUser
from .models import AppUser
from .passwords import generate_temp_password

logger = get_logger("domains.auth.users")


@dataclass(frozen=True, slots=True)
class UserPage:
    rows: list[AppUser]
    total: int


@dataclass(frozen=True, slots=True)
class UserWithTempPassword:
    user: AppUser
    temporary_password: str


async def list_users(db: AsyncSession, *, page: int, page_size: int) -> UserPage:
    total = (await db.execute(select(func.count()).select_from(AppUser))).scalar_one()
    rows = (
        (await db.execute(select(AppUser).order_by(AppUser.id).offset((page - 1) * page_size).limit(page_size)))
        .scalars()
        .all()
    )
    return UserPage(rows=list(rows), total=total)


async def get_user(db: AsyncSession, user_id: int) -> AppUser:
    row = await db.get(AppUser, user_id)
    if row is None:
        raise SemanticHTTPException(code="resource_not_found", details={"resource": "user", "id": user_id})
    return row


async def create_user(db: AsyncSession, *, login_id: str, name: str, org: str, role: str) -> UserWithTempPassword:
    """임시 비밀번호를 발급해 만든다. 계정은 첫 로그인 때 비밀번호를 바꿔야 한다."""
    password = generate_temp_password()
    try:
        row = await service.create_user(
            db, login_id=login_id, name=name, org=org, role=role, password=password, must_change_password=True
        )
    except service.LoginIdTakenError as exc:
        raise SemanticHTTPException(code="user_login_id_taken", details={"loginId": login_id}) from exc
    return UserWithTempPassword(user=row, temporary_password=password)


async def _lock_active_admin_ids(db: AsyncSession) -> list[int]:
    return list(
        (
            await db.execute(
                select(AppUser.id)
                .where(AppUser.role == ADMIN_ROLE, AppUser.is_active.is_(True))
                .order_by(AppUser.id)
                .with_for_update()
            )
        ).scalars()
    )


async def update_user(
    db: AsyncSession, actor: AuthUser, user_id: int, *, name: str, org: str, role: str, is_active: bool
) -> AppUser:
    stays_active_admin = role == ADMIN_ROLE and is_active
    # 잠금을 대상 행 읽기보다 먼저 잡는다 — 잠근 뒤에 읽어야 동시 변경이 commit 한 값을 보고, 잠금 순서가 요청마다 같아 교착이 없다
    active_admin_ids = [] if stays_active_admin else await _lock_active_admin_ids(db)
    row = await get_user(db, user_id)
    if row.id == actor.id and (role != row.role or not is_active):
        raise SemanticHTTPException(code="user_self_change_forbidden", details={"action": "update"})
    if row.id in active_admin_ids and len(active_admin_ids) == 1:
        raise SemanticHTTPException(code="user_last_admin_required")
    deactivating = row.is_active and not is_active
    row.name = name
    row.org = org
    row.role = role
    row.is_active = is_active
    if deactivating:
        row.token_version = AppUser.token_version + 1
    await db.flush()
    await db.refresh(row)
    logger.info("user updated", extra={"user_id": row.id, "actor_id": actor.id, "role": role, "is_active": is_active})
    return row


async def reset_password(db: AsyncSession, actor: AuthUser, user_id: int) -> UserWithTempPassword:
    """기존 세션을 모두 끊고 · 잠금을 풀고 · 임시 비밀번호를 발급한다."""
    row = await get_user(db, user_id)
    if row.id == actor.id:
        raise SemanticHTTPException(code="user_self_change_forbidden", details={"action": "password_reset"})
    password = generate_temp_password()
    row = await service.reset_password_row(db, row, password)
    return UserWithTempPassword(user=row, temporary_password=password)
