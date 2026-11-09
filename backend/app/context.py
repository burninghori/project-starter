"""요청 단위 상관 식별자(request_id)를 보관한다.

HTTP 경계(`middleware.request_context`)가 요청마다 값을 세우고, 로그 필터 · 오류 응답이 읽는다.
"""

from contextvars import ContextVar
from uuid import uuid4

# 요청 밖(부팅·워커 루프)임을 나타내는 값. 외부 x-request-id 로는 채택하지 않는다.
NO_REQUEST_ID = "-"

request_id_var: ContextVar[str] = ContextVar("request_id", default=NO_REQUEST_ID)


def new_request_id() -> str:
    """로그·응답 헤더에 쓰는 짧은 무작위 식별자."""
    return uuid4().hex[:12]


def get_request_id() -> str:
    """현재 요청 식별자. 요청 밖에서는 `-`."""
    return request_id_var.get()
