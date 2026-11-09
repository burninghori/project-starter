"""`python -m app.domains.auth.reset_password --login-id …` — 비밀번호 초기화.

다른 사용자는 관리자가 사용자 관리 API(`POST /users/{id}/password-reset`)로 초기화한다. 이 명령은 API 를 쓸 관리자가 없을 때 —
관리자 본인이 비밀번호를 잊었거나 계정이 잠겼을 때 — 의 경로다. 서버가 새 임시 비밀번호를 발급해 표준 출력으로 한 번만 보여 주고,
`token_version` 을 +1 해 그 사용자의 기존 세션을 모두 끊고 · 로그인 잠금을 풀고 · 첫 로그인 때 바꾸게 한다(결정 0006).
없는 아이디면 아무것도 바꾸지 않고 실패한다.
"""

import argparse
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from . import service
from ._cli import EXIT_OK, LOGIN_ID_MAX, bounded_text, print_temp_password, run_command
from .passwords import generate_temp_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="사용자의 비밀번호를 임시 비밀번호로 초기화한다")
    parser.add_argument("--login-id", required=True, help="초기화할 로그인 아이디")
    args = parser.parse_args(argv)
    login_id = bounded_text(parser, "--login-id", args.login_id, LOGIN_ID_MAX)

    async def action(db: AsyncSession) -> int:
        password = generate_temp_password()
        await service.reset_password(db, login_id=login_id, new_password=password)
        print_temp_password(login_id, password)
        return EXIT_OK

    return run_command(action)


if __name__ == "__main__":
    sys.exit(main())
