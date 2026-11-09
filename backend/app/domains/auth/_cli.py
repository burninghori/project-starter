"""인증 명령(seed_admin · reset_password)의 공통 뼈대.

로깅·DB 엔진 수명을 세우고 세션 하나에서 동작을 돌린 뒤 정리한다(`app.worker` 와 같은 꼴).
`AuthCommandError` 는 표준 오류로 알리고 종료 코드 1, 그 밖의 예외는 그대로 올린다(스택이 원인을 담는다).
"""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...db.engine import dispose_engine, init_engine, session_scope
from ...logging import setup_logging
from .service import AuthCommandError

EXIT_OK = 0
EXIT_FAILED = 1

LOGIN_ID_MAX = 64


def run_command(action: Callable[[AsyncSession], Awaitable[int]]) -> int:
    return asyncio.run(_run(action))


async def _run(action: Callable[[AsyncSession], Awaitable[int]]) -> int:
    setup_logging(settings.log_level)
    init_engine()
    try:
        async with session_scope() as db:
            return await action(db)
    except AuthCommandError as exc:
        print(f"실패: {exc}", file=sys.stderr)
        return EXIT_FAILED
    finally:
        await dispose_engine()


def bounded_text(parser: argparse.ArgumentParser, option: str, value: str, max_length: int) -> str:
    """DB 컬럼 길이를 넘는 값은 DB 오류가 아니라 사용법 오류로 끝낸다."""
    if not value.strip():
        parser.error(f"{option} 은(는) 비울 수 없다")
    if len(value) > max_length:
        parser.error(f"{option} 은(는) {max_length}자 이하여야 한다")
    return value


def print_temp_password(login_id: str, password: str) -> None:
    """표준 출력에만, 한 번만. 로거를 쓰지 않는다 — 로그 저장소에 비밀번호가 쌓이면 안 된다."""
    print(f"계정: {login_id}")
    print(f"임시 비밀번호(지금 한 번만 보인다, 로그에 남지 않는다): {password}")
    print("첫 로그인 때 비밀번호를 바꿔야 다른 화면을 쓸 수 있다.")
