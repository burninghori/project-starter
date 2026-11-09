"""내려받기 응답의 공통 조각 — 원본 파일을 첨부로 흘릴 때 쓰는 헤더."""

from urllib.parse import quote

# ASCII 대체 이름에서 그대로 둘 수 없는 글자 — 따옴표는 헤더를 끊고, 경로 구분자는 저장 위치를 바꿀 수 있다
_UNSAFE_IN_ASCII_NAME = frozenset('"\\/')


def content_disposition(file_name: str) -> str:
    """첨부 파일 이름 헤더 — RFC 6266. 한글 이름은 `filename*`(UTF-8 퍼센트 인코딩, `/` 포함 전부 인코딩)로, 그 앞의 `filename` 은
    ASCII 대체다(인쇄 가능한 ASCII 가 아니거나 따옴표·경로 구분자면 `_`). 파일명 검증은 업로드가 하고 여기는 방어다."""
    ascii_name = "".join(
        ch if ch.isascii() and ch.isprintable() and ch not in _UNSAFE_IN_ASCII_NAME else "_" for ch in file_name
    )
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name, safe='')}"
