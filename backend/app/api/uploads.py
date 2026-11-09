"""업로드 경계의 공통 조각 — 파일 이름 규칙과 본문을 읽기 전 길이 검사(api.md 「업로드」).

파일을 받는 엔드포인트가 모두 같은 규칙으로 막는다. 한도 값은 쓰는 쪽이 정한다.
"""

import re
from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Request, Response
from fastapi.routing import APIRoute

from .error_contract import SemanticHTTPException

# 한도의 MB 는 1,048,576 바이트(api.md 「업로드」 — 화면의 한도 표시와 같은 단위)
MEGABYTE = 1_048_576
MAX_FILE_NAME_CHARS = 255
# 본문 길이 검사에서 multipart 포장(경계 줄 · part 머리)에 주는 여유 — 파일 크기의 정확한 검사는 파싱 뒤에 한다
ENVELOPE_SLACK_BYTES = MEGABYTE
# 파일 이름에 들어갈 수 없는 글자 — NUL 은 DB 가 받지 않고, 제어 문자는 화면 · 내려받기 헤더를 깨뜨린다
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_PATH_SEPARATORS = re.compile(r"[/\\]")


def file_basename(raw_name: str) -> str:
    """경로 부분을 뗀 이름. 브라우저 · OS 에 따라 `/` 또는 `\\` 가 오므로 둘 다 뗀다."""
    return _PATH_SEPARATORS.split(raw_name)[-1]


def checked_file_name(raw_name: str) -> str:
    """올린 이름 → 저장할 이름(경로를 뗀 것). 비었거나 255자를 넘거나 제어 문자가 있으면 422 `upload_file_name_invalid`."""
    name = file_basename(raw_name)
    if not name or len(name) > MAX_FILE_NAME_CHARS or _CONTROL_CHARS.search(name) is not None:
        raise SemanticHTTPException(code="upload_file_name_invalid", details={"fileName": name or raw_name})
    return name


def require_content_length(request: Request, limit: int) -> None:
    """본문을 읽기 전에 `Content-Length` 를 본다 — 없으면 411, 한도(+ 포장 여유)를 넘으면 413.

    길이를 모르면 받기 전에 끊을 수 없어 거부한다(브라우저는 FormData 전송에 항상 길이를 붙인다).
    FastAPI 는 의존성을 풀기 전에 본문부터 읽으므로(`routing.get_request_handler`) 의존성으로는 늦다 — `length_checked_route`
    가 만든 라우트가 핸들러 바깥에서 부른다.
    """
    raw = request.headers.get("content-length")
    try:
        content_length = int(raw) if raw is not None else None
    except ValueError:
        content_length = None
    if content_length is None:
        raise SemanticHTTPException(code="upload_length_required")
    if content_length > limit + ENVELOPE_SLACK_BYTES:
        raise SemanticHTTPException(
            code="upload_too_large", details={"scope": "request", "limit": limit, "actual": content_length}
        )


def length_checked_route(limit: Callable[[], int]) -> type[APIRoute]:
    """본문을 읽기 전에 길이를 검사하는 라우트 클래스 — 한도를 넘는 본문을 디스크에 받지 않는다. `limit` 은 요청마다 부른다.

    인증(401)은 미들웨어가 그 앞에서 끝내고, 권한 검사(403)는 본문을 읽은 뒤라 권한이 없는 요청은 411 · 413 이 먼저일 수 있다.
    """

    class LengthCheckedRoute(APIRoute):
        def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
            original = super().get_route_handler()

            async def handler(request: Request) -> Response:
                require_content_length(request, limit())
                return await original(request)

            return handler

    return LengthCheckedRoute
