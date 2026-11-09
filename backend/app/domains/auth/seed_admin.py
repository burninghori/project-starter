"""`python -m app.domains.auth.seed_admin` — 관리자 계정 시드(멱등).

`ADMIN_LOGIN_ID`·`ADMIN_INITIAL_PASSWORD` 를 읽어 관리자(역할 admin, 기능 권한 3개 true, `must_change_password`)를
만든다. 이미 있으면 아무것도 바꾸지 않는다. 비밀번호가 마이그레이션 파일에 남지 않게 마이그레이션이 아니라 명령이다
(backend-conventions 「시드」). 계속 남는 유일한 계정 생성 명령이다.
"""

import sys

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import AdminSeedSettings
from . import service
from ._cli import EXIT_OK, run_command
from .passwords import MAX_BYTES, MIN_LENGTH, password_rule_violation


def main() -> int:
    seed = AdminSeedSettings()  # pyright: ignore[reportCallIssue]  # 값은 환경변수에서 채운다

    async def action(db: AsyncSession) -> int:
        password = seed.admin_initial_password.get_secret_value()
        # 환경변수 값이라 여기(경계)서 규칙을 먼저 본다 — 해시 단계의 예외(스택 트레이스) 대신 사유 한 줄로 끝낸다. 값은 출력하지 않는다
        violation = password_rule_violation(password)
        if violation is not None:
            raise service.AuthCommandError(
                f"ADMIN_INITIAL_PASSWORD 가 비밀번호 규칙({MIN_LENGTH}자 이상 · UTF-8 {MAX_BYTES}바이트 이하 · 공백 없음)에 "
                f"맞지 않는다: {violation}"
            )
        created = await service.seed_admin(db, login_id=seed.admin_login_id, password=password)
        if created is None:
            print(f"관리자 계정 {seed.admin_login_id} 이(가) 이미 있다 — 바꾸지 않았다")
        else:
            print(f"관리자 계정 {seed.admin_login_id} 을(를) 만들었다 — 첫 로그인 때 비밀번호를 바꿔야 한다")
        return EXIT_OK

    return run_command(action)


if __name__ == "__main__":
    sys.exit(main())
