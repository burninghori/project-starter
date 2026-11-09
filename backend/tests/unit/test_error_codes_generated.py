"""frontend 오류 code 타입이 backend 목록과 같은가 — code 를 더하고 make gen-error-codes 를 빠뜨리면 실패한다."""

from scripts.generate_error_codes import OUTPUT, render


def test_frontend_error_codes_are_up_to_date() -> None:
    assert OUTPUT.read_text(encoding="utf-8") == render(), "make gen-error-codes 로 다시 만든다"
