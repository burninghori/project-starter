"""라우터용 DB 세션 의존성 — 요청 하나에 세션 하나, 성공 시 commit·예외 시 rollback.

commit·rollback 은 핸들러가 돌아온 뒤, **응답을 보내기 전에** 끝난다(`scope="function"`). 그래서 2xx 를 받은 클라이언트의
다음 요청은 그 쓰기를 보고, commit 이 실패하면 성공 응답 대신 오류 응답(500)이 나간다. FastAPI 는 scope 를 정하지 않은
yield 의존성을 응답을 보낸 뒤에 정리하므로 지정을 빼지 않는다. 스트리밍 응답은 본문을 보내기 전에 세션이 닫힌다 —
본문 생성기에서 세션을 쓰지 않는다.

사용 예: async def get_item(item_id: int, db: AsyncSession = DbDep) -> ItemOut: ...
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .engine import session_scope


async def _db() -> AsyncGenerator[AsyncSession]:
    async with session_scope() as session:
        yield session


DbDep = Depends(_db, scope="function")
