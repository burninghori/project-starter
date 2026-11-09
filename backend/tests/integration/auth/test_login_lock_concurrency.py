"""로그인 잠금의 동시성 — 판정이 요청 시작 때 읽은 값이 아니라 UPDATE 순간의 행으로 이뤄지는가.

요청마다 세션 하나(실제 API 처럼 각자 commit)로 서비스 함수를 동시에 부른다.
"""

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.api.error_contract import SemanticHTTPException
from app.config import settings
from app.domains.auth import service
from app.domains.auth.passwords import verify_password

PASSWORD = "right-pass-123"


async def _new_user(engine: AsyncEngine) -> str:
    login_id = f"race-{uuid4().hex[:10]}"
    async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
        await service.create_user(
            session,
            login_id=login_id,
            name="동시",
            org="테스트",
            role="member",
            password=PASSWORD,
            must_change_password=False,
        )
    return login_id


async def _attempt(engine: AsyncEngine, login_id: str, password: str) -> str:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            await service.authenticate(session, login_id, password)
        except SemanticHTTPException as exc:
            await session.rollback()
            return exc.code
        await session.commit()
        return "ok"


async def test_concurrent_failures_count_only_up_to_the_limit(db_engine: AsyncEngine) -> None:
    login_id = await _new_user(db_engine)
    attempts = settings.login_max_failures * 3

    codes = await asyncio.gather(*(_attempt(db_engine, login_id, "wrong-pass") for _ in range(attempts)))

    # 한도 직전까지만 「틀림」을 알려 주고 나머지는 잠금이다 — 동시에 보내도 한도를 넘는 추측의 결과를 얻지 못한다
    assert codes.count("auth_invalid_credentials") == settings.login_max_failures - 1
    assert codes.count("auth_login_locked") == attempts - (settings.login_max_failures - 1)
    assert await _attempt(db_engine, login_id, PASSWORD) == "auth_login_locked"


async def test_lock_set_during_a_correct_attempt_wins(db_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    login_id = await _new_user(db_engine)

    def verify_while_another_request_locks(raw: str, password_hash: str) -> bool:
        # 이 요청이 잠기지 않은 행을 읽은 뒤, 해시 검증 중에 다른 요청이 잠금을 commit 했다
        async def lock() -> None:
            async with AsyncSession(db_engine) as session, session.begin():
                await session.execute(
                    text("UPDATE app_user SET locked_until = now() + interval '10 minutes' WHERE login_id = :id"),
                    {"id": login_id},
                )

        asyncio.run(lock())
        return verify_password(raw, password_hash)

    monkeypatch.setattr(service, "verify_password", verify_while_another_request_locks)

    assert await _attempt(db_engine, login_id, PASSWORD) == "auth_login_locked"
