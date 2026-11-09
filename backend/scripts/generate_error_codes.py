"""오류 code 목록(backend)을 frontend TypeScript 타입으로 옮긴다.

정본은 `app/api/error_contract.py` 의 `ApiErrorCode`·`ERROR_CODE_STATUS` 다. 이 스크립트는 그것을
`frontend/src/api/error-codes.generated.ts` 로 쓴다. frontend 의 문구 표(`error-messages.ts`)가 이 타입을
`Record<ApiErrorCode, …>` 로 받으므로, code 를 더하고 문구를 빠뜨리면 TypeScript 컴파일이 실패한다.

    uv run python -m scripts.generate_error_codes          # 다시 만든다 (루트에서 make gen-error-codes)
    uv run python -m scripts.generate_error_codes --check  # 생성물이 최신인지 확인만 한다

생성물이 최신인지는 unit 테스트(`tests/unit/test_error_codes_generated.py`)도 매번 확인한다.
"""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import get_args

from app.api.error_contract import ERROR_CODE_STATUS, ERROR_CONTRACT_VERSION, ApiErrorFamily

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "error-codes.generated.ts"


def _union(name: str, values: Sequence[str]) -> str:
    return f"export type {name} =\n" + "\n".join(f'  | "{value}"' for value in values) + "\n"


def render() -> str:
    codes = list(ERROR_CODE_STATUS)
    status_rows = "\n".join(f"  {code}: {status}," for code, status in ERROR_CODE_STATUS.items())
    code_rows = "\n".join(f'  "{code}",' for code in codes)
    return (
        "// 자동 생성 — backend/scripts/generate_error_codes.py 가 backend/app/api/error_contract.py 에서 만든다.\n"
        "// 손으로 고치지 않는다. 다시 만들기: make gen-error-codes\n"
        "\n"
        f'export const API_ERROR_CONTRACT_VERSION = "{ERROR_CONTRACT_VERSION}"\n'
        "\n"
        + _union("ApiErrorFamily", [str(value) for value in get_args(ApiErrorFamily)])
        + "\n"
        + _union("ApiErrorCode", codes)
        + "\n"
        + f"export const API_ERROR_CODES: readonly ApiErrorCode[] = [\n{code_rows}\n]\n"
        + "\n"
        + f"export const API_ERROR_STATUS: Record<ApiErrorCode, number> = {{\n{status_rows}\n}}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="오류 code 목록을 frontend 타입으로 옮긴다")
    parser.add_argument("--check", action="store_true", help="생성물이 최신인지 확인만 한다")
    args = parser.parse_args()

    expected = render()
    current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else None
    if args.check:
        if current != expected:
            print(f"{OUTPUT} 가 오래됐다 — make gen-error-codes 로 다시 만든다", file=sys.stderr)
            return 1
        print("error-codes.generated.ts 최신")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"썼다: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
