"""테스트에서만 비밀번호 해시(bcrypt) 강도를 낮춘다 — 운영 코드 · 설정은 그대로다.

사용자를 만들고 로그인할 때마다 운영 강도(12, 건당 약 0.16초)로 해시 · 검증하면 테스트 시간의 절반 가까이를 쓴다. 해시 · 검증
코드(`app/domains/auth/passwords.py`)는 그대로 타고 소금(salt)을 만드는 `bcrypt.gensalt` 의 강도만 4 로 바꾼다 — 강도는 해시 문자열에
남고 검증이 그 값을 따르므로 비밀번호 동작(로그인 성공 · 실패, 변경, 임시 비밀번호)은 지금과 같이 테스트된다.

테스트 세션이 시작할 때 한 번 바꾼다(`pytest_configure`) — 세션 범위 픽스처(공용 관리자 계정)보다 먼저여야 그 계정도 낮은 강도로
해시된다. 테스트 함수마다 `monkeypatch` 로 바꾸지 않는다 — 다른 테스트가 바꿔 끼운 것과 정리 순서가 엉킨다. 운영 강도는
`PRODUCTION_GENSALT` 로 되돌려 확인한다(`tests/unit/auth/test_passwords.py`).
"""

import bcrypt

TEST_ROUNDS = 4
PRODUCTION_GENSALT = bcrypt.gensalt


def _test_gensalt(rounds: int = TEST_ROUNDS, prefix: bytes = b"2b") -> bytes:
    """운영 코드가 강도(`rounds`)를 넘겨도 테스트 강도를 쓴다 — 접두어(알고리즘 판)만 그대로 넘긴다. `rounds` 는 키워드로 부르는
    호출과 맞추려고 이름만 받는다."""
    return PRODUCTION_GENSALT(rounds=TEST_ROUNDS, prefix=prefix)


def pytest_configure() -> None:
    bcrypt.gensalt = _test_gensalt
