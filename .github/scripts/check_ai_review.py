"""AI 리뷰 결과 게이트 — claude-code-action 의 실행 기록(execution_file)으로 리뷰가 실제로 끝났는지 판정한다.

액션은 세션이 오류로 끝나도 스텝을 성공으로 끝내 「거짓 초록」이 생긴다. 실행 기록의 마지막 `result` 메시지를 읽어
아래면 실패(종료 코드 1)로 바꾼다.

- 기록 파일이 없거나 읽을 수 없다(종료 코드 2 — 리뷰가 아니라 게이트가 판정을 못 한 것)
- `result` 메시지가 없다 / `is_error` 가 참이다
- 턴 수가 너무 적다(토큰·인증 문제로 첫 응답에서 죽은 경우. 리뷰는 파일을 읽고 코멘트를 달아야 하므로 몇 턴 이상 쓴다)

stdlib 만 쓴다(러너에 의존성 설치 없이 돈다).
"""

import json
import sys

MIN_TURNS = 3


def main(path: str) -> int:
    if not path:
        print("게이트: execution_file 출력이 비어 있다 — 액션이 실행 기록을 만들기 전에 끝났다", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as handle:
            messages = json.load(handle)
    except (OSError, ValueError) as exc:
        print(f"게이트: 실행 기록을 읽지 못했다({path}): {exc}", file=sys.stderr)
        return 2
    if not isinstance(messages, list):
        print("게이트: 실행 기록이 메시지 목록이 아니다", file=sys.stderr)
        return 2

    results = [m for m in messages if isinstance(m, dict) and m.get("type") == "result"]
    if not results:
        print("게이트: result 메시지가 없다 — 세션이 결과 없이 끝났다", file=sys.stderr)
        return 1
    last = results[-1]
    turns = last.get("num_turns", 0)
    cost = last.get("total_cost_usd")
    print(f"게이트: subtype={last.get('subtype')} is_error={last.get('is_error')} turns={turns} cost={cost}")
    if last.get("is_error"):
        print(f"게이트: 세션이 오류로 끝났다: {str(last.get('result'))[:500]}", file=sys.stderr)
        return 1
    if not isinstance(turns, int) or turns < MIN_TURNS:
        print(f"게이트: 턴 수 {turns} — 리뷰를 하지 않고 끝났다(토큰·권한 문제일 수 있다, 잡 로그 참고)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
