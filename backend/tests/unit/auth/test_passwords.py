"""비밀번호 규칙·해시 — 결정 0006 의 경계값."""

import bcrypt
import pytest

from app.domains.auth.passwords import (
    MAX_BYTES,
    MIN_LENGTH,
    burn_verification_cost,
    generate_temp_password,
    hash_password,
    password_rule_violation,
    verify_password,
)
from tests.plugins.password_cost import PRODUCTION_GENSALT, TEST_ROUNDS

# 「가」는 UTF-8 3바이트 — 24자가 정확히 72바이트
HANGUL_72_BYTES = "가" * 24


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("a" * (MIN_LENGTH - 1), "too_short", id="7자"),
        pytest.param("a" * MIN_LENGTH, None, id="8자"),
        pytest.param("가" * 7, "too_short", id="한글 7자(21바이트)"),
        pytest.param("가" * 8, None, id="한글 8자(24바이트)"),
        pytest.param("a" * MAX_BYTES, None, id="72바이트"),
        pytest.param("a" * (MAX_BYTES + 1), "too_long", id="73바이트"),
        pytest.param(HANGUL_72_BYTES, None, id="한글 24자 = 72바이트"),
        pytest.param(HANGUL_72_BYTES + "a", "too_long", id="한글 24자 + 1 = 73바이트"),
        pytest.param(" abcdefgh", "whitespace", id="앞 공백"),
        pytest.param("abcdefgh ", "whitespace", id="뒤 공백"),
        pytest.param("abcd efgh", "whitespace", id="중간 공백"),
        pytest.param("abcd\nefgh", "whitespace", id="줄바꿈"),
        pytest.param("abcd\tefgh", "whitespace", id="탭"),
        pytest.param("12345678", None, id="숫자만 — 조합 요구 없음"),
    ],
)
def test_rule_boundaries(raw: str, expected: str | None) -> None:
    assert password_rule_violation(raw) == expected


def test_temp_password_is_unique_and_satisfies_rules() -> None:
    samples = {generate_temp_password() for _ in range(50)}

    assert len(samples) == 50
    assert all(password_rule_violation(sample) is None for sample in samples)


def test_hash_roundtrip() -> None:
    password_hash = hash_password("correct-horse-1")

    assert verify_password("correct-horse-1", password_hash) is True
    assert verify_password("correct-horse-2", password_hash) is False


def test_hash_uses_the_production_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    # 테스트는 세션 시작 때 강도를 낮춘다(tests/plugins/password_cost.py) — 이 테스트만 운영 소금으로 되돌려 운영 강도(12)를 확인한다.
    # 72바이트 초과 검증 · `burn_verification_cost` 는 여기서 부르지 않는다 — 시간 평준화 해시는 처음 불린 때의 강도로 프로세스 끝까지
    # 캐시되어, 여기서 만들면 뒤 테스트 전부가 운영 강도로 검증한다
    monkeypatch.setattr(bcrypt, "gensalt", PRODUCTION_GENSALT)

    hashed = hash_password("correct-horse")

    assert hashed.startswith("$2b$12$")
    assert verify_password("correct-horse", hashed)


def test_tests_hash_with_the_lowered_cost() -> None:
    # 테스트 강도(4)가 실제로 쓰이는지 — 운영 코드가 `from bcrypt import gensalt` 처럼 이름을 직접 가져오거나 플러그인 등록이 빠지면
    # 테스트는 모두 통과한 채 운영 강도로 돌아 시간만 두 배가 된다. 그 회귀를 여기서 잡는다
    assert hash_password("correct-horse").startswith(f"$2b${TEST_ROUNDS:02d}$")


def test_hash_refuses_rule_violation() -> None:
    with pytest.raises(ValueError, match="too_short"):
        hash_password("short")


def test_over_72_bytes_is_mismatch_not_error() -> None:
    password_hash = hash_password("a" * MAX_BYTES)

    # bcrypt 5 는 73바이트부터 예외를 내지만 로그인은 불일치로 답해야 한다
    assert verify_password("a" * (MAX_BYTES + 1), password_hash) is False


def test_burn_verification_cost_accepts_any_input() -> None:
    burn_verification_cost("")
    burn_verification_cost("x" * 500)
