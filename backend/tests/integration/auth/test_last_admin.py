"""활성 관리자는 늘 한 명 이상 남는다 — 강등 · 사용 중지가 마지막 관리자를 없애면 409."""

import asyncio
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.error_contract import SemanticHTTPException
from app.domains.auth import service, users
from app.domains.auth.deps import AuthUser
from app.domains.auth.models import AppUser


async def _admin(db: AsyncSession) -> AppUser:
    return await service.create_user(
        db,
        login_id=f"adm-{uuid4().hex[:10]}",
        name="관리자",
        org="테스트",
        role="admin",
        password="admin-pass-1",
        must_change_password=False,
    )


async def _change(db: AsyncSession, actor: AuthUser, target: AppUser, *, role: str, is_active: bool) -> str:
    try:
        await users.update_user(db, actor, target.id, name=target.name, org=target.org, role=role, is_active=is_active)
    except SemanticHTTPException as exc:
        return exc.code
    return "ok"


async def test_last_active_admin_cannot_be_demoted_or_deactivated(db_session: AsyncSession) -> None:
    # 바깥 트랜잭션 안이라 테스트가 끝나면 되돌아간다 — 다른 테스트의 관리자를 잠시 없는 것으로 친다
    await db_session.execute(text("UPDATE app_user SET is_active = false WHERE role = 'admin'"))
    actor_row, last = await _admin(db_session), await _admin(db_session)
    actor = AuthUser.from_row(actor_row)
    # 요청을 보낸 관리자가 그 사이 사용 중지됐다 — 남은 활성 관리자는 last 하나
    await db_session.execute(text("UPDATE app_user SET is_active = false WHERE id = :id"), {"id": actor_row.id})

    assert await _change(db_session, actor, last, role="member", is_active=True) == "user_last_admin_required"
    assert await _change(db_session, actor, last, role="admin", is_active=False) == "user_last_admin_required"
    # 관리자로 남는 변경(이름 · 소속)은 된다
    assert await _change(db_session, actor, last, role="admin", is_active=True) == "ok"

    await _admin(db_session)
    assert await _change(db_session, actor, last, role="member", is_active=True) == "ok"


async def test_two_admins_demoting_each_other_at_once_leaves_one(db_engine: AsyncEngine) -> None:
    async with AsyncSession(db_engine, expire_on_commit=False) as session, session.begin():
        others = list(
            (
                await session.execute(
                    text("UPDATE app_user SET is_active = false WHERE role = 'admin' AND is_active RETURNING id")
                )
            ).scalars()
        )
        first, second = await _admin(session), await _admin(session)
    try:

        async def demote(actor: AppUser, target: AppUser) -> str:
            async with AsyncSession(db_engine, expire_on_commit=False) as session:
                code = await _change(session, AuthUser.from_row(actor), target, role="member", is_active=True)
                await (session.commit() if code == "ok" else session.rollback())
                return code

        codes = await asyncio.gather(demote(first, second), demote(second, first))

        assert sorted(codes) == ["ok", "user_last_admin_required"]
    finally:
        async with AsyncSession(db_engine) as session, session.begin():
            await session.execute(text("UPDATE app_user SET is_active = true WHERE id = ANY(:ids)"), {"ids": others})
