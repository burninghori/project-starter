"""요청마다 request_id 를 세우고 접근 로그 한 줄을 남기는 ASGI 미들웨어.

- 들어온 `x-request-id` 가 형식에 맞으면 그대로 쓰고(로드밸런서·프록시 상관), 아니면 새로 만든다.
- 응답 헤더 `x-request-id` 로 돌려준다. 화면 오류 안내의 문의 번호가 이 값이다.
- `scope["state"]["request_id"]` 에도 남긴다 — 처리되지 않은 예외 처리기는 이 미들웨어 바깥에서
  돌아 ContextVar 를 읽지 못한다.

BaseHTTPMiddleware 가 아니라 순수 ASGI 로 쓴다. 응답 스트리밍과 ContextVar 전파가 단순하다.
"""

import re
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ..context import new_request_id, request_id_var
from ..logging import get_logger

logger = get_logger("http")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# 헬스체크는 로드밸런서가 수 초마다 부른다. 접근 로그를 남기지 않는다.
_QUIET_PATHS = frozenset({"/api/health"})


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope["headers"])
        incoming = headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = incoming if _REQUEST_ID_PATTERN.match(incoming) else new_request_id()
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            path = scope.get("path", "")
            if path not in _QUIET_PATHS:
                logger.info(
                    "request completed",
                    extra={
                        "method": scope.get("method"),
                        "path": path,
                        "status": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    },
                )
            request_id_var.reset(token)
