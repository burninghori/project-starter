"""사용자 관리 API — api.md 「사용자 관리」. 모든 경로가 관리자 전용이다(`RequireAdmin`)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.schemas import BIGINT_MAX, IdPath, PageEnvelope, page_count_for
from ...db.deps import DbDep
from . import users
from .deps import AuthUser, RequireAdmin
from .schemas import UserCreateIn, UserEnvelope, UserOut, UserUpdateIn, UserWithTempPasswordOut

router = APIRouter(prefix="/users", tags=["users"])

PAGE_SIZE = 50
# OFFSET = (page - 1) × PAGE_SIZE 가 bigint 를 넘지 않는 가장 큰 쪽 번호(backend-conventions 「요청 입력」)
MAX_PAGE = BIGINT_MAX // PAGE_SIZE


def _with_temp_password(result: users.UserWithTempPassword) -> UserWithTempPasswordOut:
    return UserWithTempPasswordOut(
        user=UserOut.model_validate(result.user), temporary_password=result.temporary_password
    )


@router.get("")
async def list_users(
    page: Annotated[int, Query(ge=1, le=MAX_PAGE)],
    _admin: AuthUser = RequireAdmin,
    db: AsyncSession = DbDep,
) -> PageEnvelope[UserOut]:
    result = await users.list_users(db, page=page, page_size=PAGE_SIZE)
    return PageEnvelope[UserOut](
        rows=[UserOut.model_validate(row) for row in result.rows],
        total=result.total,
        page_count=page_count_for(result.total, PAGE_SIZE),
    )


@router.post("", status_code=201)
async def create_user(
    body: UserCreateIn, _admin: AuthUser = RequireAdmin, db: AsyncSession = DbDep
) -> UserWithTempPasswordOut:
    result = await users.create_user(db, login_id=body.login_id, name=body.name, org=body.org, role=body.role)
    return _with_temp_password(result)


@router.get("/{user_id}")
async def get_user(user_id: IdPath, _admin: AuthUser = RequireAdmin, db: AsyncSession = DbDep) -> UserEnvelope:
    return UserEnvelope(user=UserOut.model_validate(await users.get_user(db, user_id)))


@router.put("/{user_id}")
async def update_user(
    user_id: IdPath, body: UserUpdateIn, admin: AuthUser = RequireAdmin, db: AsyncSession = DbDep
) -> UserEnvelope:
    row = await users.update_user(
        db, admin, user_id, name=body.name, org=body.org, role=body.role, is_active=body.is_active
    )
    return UserEnvelope(user=UserOut.model_validate(row))


@router.post("/{user_id}/password-reset")
async def reset_password(
    user_id: IdPath, admin: AuthUser = RequireAdmin, db: AsyncSession = DbDep
) -> UserWithTempPasswordOut:
    return _with_temp_password(await users.reset_password(db, admin, user_id))
