"""비밀번호 규칙과 해시의 단일 정본(결정 0006).

규칙: 8자 이상 · UTF-8 72바이트 이하(bcrypt 입력 상한) · 공백·줄바꿈 금지 · 조합 요구 없음.
frontend(`src/api/auth/password-rules.ts`)가 같은 규칙으로 입력을 미리 검사한다 — 값을 바꾸면 양쪽을 함께 바꾼다.

해시는 `bcrypt` 패키지를 직접 쓴다(래퍼 없음). bcrypt 5 는 72바이트를 넘는 입력을 예외로 내므로 규칙 밖 입력은
여기서 걸러 불일치로 답한다 — 단, 응답 시간으로 계정 존재가 드러나지 않게 해시 검증을 한 번은 치른다.
"""

import secrets
from functools import cache
from typing import Literal

import bcrypt

MIN_LENGTH = 8
MAX_BYTES = 72
# 16자(URL-safe base64). 공백이 없고 72바이트를 넘지 않아 규칙을 스스로 만족한다
TEMP_PASSWORD_BYTES = 12

PasswordRuleViolation = Literal["too_short", "too_long", "whitespace"]


def password_rule_violation(raw: str) -> PasswordRuleViolation | None:
    """규칙을 어기면 그 사유, 맞으면 None. 비밀번호 변경 API·명령의 임시 비밀번호가 같은 함수를 쓴다."""
    if len(raw) < MIN_LENGTH:
        return "too_short"
    if len(raw.encode("utf-8")) > MAX_BYTES:
        return "too_long"
    if any(ch.isspace() for ch in raw):
        return "whitespace"
    return None


def hash_password(raw: str) -> str:
    """규칙에 맞는 비밀번호만 받는다 — 호출부가 먼저 `password_rule_violation` 으로 거른다."""
    violation = password_rule_violation(raw)
    if violation is not None:
        raise ValueError(f"규칙에 맞지 않는 비밀번호는 해시하지 않는다: {violation}")
    return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


@cache
def _timing_equalizer_hash() -> bytes:
    """대조할 해시가 없을 때(계정 없음·규칙 밖 입력) 검증 한 번만큼 시간을 쓰는 데 대는 해시.

    대조 결과는 버린다. 무작위 값으로 프로세스당 한 번 만든다.
    """
    return bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt())


def verify_password(raw: str, password_hash: str) -> bool:
    data = raw.encode("utf-8")
    if len(data) > MAX_BYTES:
        # bcrypt 5 는 72바이트 초과를 ValueError 로 낸다. 규칙 밖 입력은 불일치이고, 시간 평준화를 위해 한 번 검증한다
        bcrypt.checkpw(data[:MAX_BYTES], _timing_equalizer_hash())
        return False
    return bcrypt.checkpw(data, password_hash.encode("ascii"))


def burn_verification_cost(raw: str) -> None:
    """계정이 없을 때도 해시 검증 한 번만큼 시간을 쓴다(아이디 존재 여부를 응답 시간으로 숨긴다)."""
    bcrypt.checkpw(raw.encode("utf-8")[:MAX_BYTES], _timing_equalizer_hash())


def generate_temp_password() -> str:
    """서버가 발급하는 임시 비밀번호(CSPRNG). 호출부(명령의 표준 출력 · 사용자 관리 API 응답)는 한 번만 보여 주고 로거에 남기지 않는다."""
    password = secrets.token_urlsafe(TEMP_PASSWORD_BYTES)
    violation = password_rule_violation(password)
    if violation is not None:  # pragma: no cover - 길이·문자 집합이 고정이라 일어나지 않는다
        raise RuntimeError(f"발급한 임시 비밀번호가 규칙을 어긴다: {violation}")
    return password
