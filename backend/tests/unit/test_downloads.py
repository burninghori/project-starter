"""원본 내려받기의 첨부 파일 이름 헤더 — 한글 이름은 `filename*`(RFC 6266) 로, `filename` 은 ASCII 대체.

파일명 검증은 업로드 쪽 일이고 여기는 방어다 — 어떤 이름이 들어와도 헤더가 끊기거나 경로가 섞이지 않는다.
"""

import pytest

from app.api.downloads import content_disposition


def test_korean_name_is_percent_encoded_with_an_ascii_fallback() -> None:
    header = content_disposition("v5 보고서 샘플.zip")

    assert header.startswith('attachment; filename="v5 ___ __.zip"; ')
    assert header.endswith("filename*=UTF-8''v5%20%EB%B3%B4%EA%B3%A0%EC%84%9C%20%EC%83%98%ED%94%8C.zip")


def test_ascii_name_is_kept() -> None:
    assert content_disposition("ORD-0001.json") == (
        "attachment; filename=\"ORD-0001.json\"; filename*=UTF-8''ORD-0001.json"
    )


@pytest.mark.parametrize(
    ("file_name", "ascii_name", "encoded"),
    [
        ('a"b.json', "a_b.json", "a%22b.json"),
        ("a/b.json", "a_b.json", "a%2Fb.json"),
        ("a\\b.json", "a_b.json", "a%5Cb.json"),
        ("x\ty.json", "x_y.json", "x%09y.json"),
    ],
)
def test_quotes_separators_and_control_chars_cannot_break_the_header(
    file_name: str, ascii_name: str, encoded: str
) -> None:
    assert content_disposition(file_name) == (f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded}")
