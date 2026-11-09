"""인증 서비스 — 세션 하나 안에서만 볼 수 있는 동작(시드 멱등, 기대 버전 조건부 변경, 초기화, 사용자 이름 조회)."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_contract import SemanticHTTPException
from app.domains.auth import service
from app.domains.auth.deps import AuthUser
from app.domains.auth.passwords import verify_password


def _login_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


async def test_seed_admin_creates_once_and_never_overwrites(db_session: AsyncSession) -> None:
    login_id = _login_id("seed")

    created = await service.seed_admin(db_session, login_id=login_id, password="change-me-1")
    again = await service.seed_admin(db_session, login_id=login_id, password="different-2")

    assert created is not None
    assert (created.role, created.must_change_password) == ("admin", True)
    assert again is None
    assert verify_password("change-me-1", created.password_hash) is True
    assert verify_password("different-2", created.password_hash) is False


async def test_create_user_rejects_duplicate_login_id(db_session: AsyncSession) -> None:
    login_id = _login_id("dup")
    await service.create_user(
        db_session,
        login_id=login_id,
        name="첫 번째",
        org="QA",
        role="admin",
        password="first-pass-1",
        must_change_password=True,
    )

    with pytest.raises(service.LoginIdTakenError):
        await service.create_user(
            db_session,
            login_id=login_id,
            name="두 번째",
            org="QA",
            role="admin",
            password="second-pass",
            must_change_password=True,
        )


async def test_change_password_with_stale_expected_version_is_409(db_session: AsyncSession) -> None:
    row = await service.create_user(
        db_session,
        login_id=_login_id("stale"),
        name="스테일",
        org="QA",
        role="admin",
        password="old-pass-1",
        must_change_password=False,
    )
    user = AuthUser.from_row(row)
    # 그 사이 관리자가 세션을 회수했다(비밀번호는 그대로)
    await db_session.execute(
        text("UPDATE app_user SET token_version = token_version + 1 WHERE id = :id"), {"id": row.id}
    )

    with pytest.raises(SemanticHTTPException) as caught:
        await service.change_password(db_session, user, "old-pass-1", "new-pass-22")

    assert caught.value.code == "auth_token_version_stale"


async def test_change_password_bumps_version_and_clears_gate(db_session: AsyncSession) -> None:
    row = await service.create_user(
        db_session,
        login_id=_login_id("chg"),
        name="변경",
        org="QA",
        role="admin",
        password="old-pass-1",
        must_change_password=True,
    )

    updated = await service.change_password(db_session, AuthUser.from_row(row), "old-pass-1", "new-pass-22")

    assert (updated.token_version, updated.must_change_password) == (1, False)
    assert verify_password("new-pass-22", row.password_hash) is True


async def test_reset_password_bumps_version_and_sets_gate(db_session: AsyncSession) -> None:
    row = await service.create_user(
        db_session,
        login_id=_login_id("rst"),
        name="초기화",
        org="QA",
        role="admin",
        password="old-pass-1",
        must_change_password=False,
    )

    reset = await service.reset_password(db_session, login_id=row.login_id, new_password="temp-pass-33")

    assert (reset.token_version, reset.must_change_password) == (1, True)
    assert verify_password("temp-pass-33", reset.password_hash) is True
    assert verify_password("old-pass-1", reset.password_hash) is False


async def test_reset_password_unknown_login_id_fails(db_session: AsyncSession) -> None:
    with pytest.raises(service.UserNotFoundError):
        await service.reset_password(db_session, login_id=_login_id("nobody"), new_password="temp-pass-33")


# ---------- 사용자 이름 조회(다른 도메인의 사람 칸) ----------


async def _make_named(db: AsyncSession, name: str) -> int:
    user = await service.create_user(
        db,
        login_id=_login_id("nm"),
        name=name,
        org="QA",
        role="admin",
        password="name-pass-1",
        must_change_password=False,
    )
    return user.id


async def test_user_names_maps_ids_and_skips_none(db_session: AsyncSession) -> None:
    first = await _make_named(db_session, "첫 사람")
    second = await _make_named(db_session, "둘째 사람")

    # 중복 id 와 None(기록된 사람 없음)이 섞여 들어와도 사람마다 한 번씩만 나온다
    names = await service.user_names(db_session, [first, None, second, first, None])

    assert names == {first: "첫 사람", second: "둘째 사람"}


@pytest.mark.parametrize("ids", [[], [None, None]])
async def test_user_names_sends_no_query_without_ids(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, ids: list[int | None]
) -> None:
    calls: list[object] = []

    async def record(*args: object, **kwargs: object) -> None:
        calls.append(args)

    monkeypatch.setattr(db_session, "execute", record)

    assert await service.user_names(db_session, ids) == {}
    assert calls == []
