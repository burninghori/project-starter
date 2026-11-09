"""예외를 semantic-v1 오류 응답으로 바꾸는 공용 처리기.

- `SemanticHTTPException`: product 코드가 낸 오류. 5xx 만 서버 로그에 남긴다(4xx 는 접근 로그로 충분).
- 프레임워크 404·405: 라우트 없음·메서드 불일치.
- 프레임워크 400: 요청 본문 파싱 실패(깨진 multipart·part 수 초과) — 클라이언트의 형식 오류라 422 `request_validation_failed` 로 답한다.
- 요청 검증 실패 422: Pydantic 오류를 `issues` 로 접는다. 사용자가 보낸 값(`input`)은 싣지 않는다.
- 처리되지 않은 예외 500: 원인은 서버 로그에만, 응답에는 requestId 만.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..logging import get_logger
from .error_contract import SemanticHTTPException, semantic_error_response, semantic_error_response_for

logger = get_logger("api.errors")

MAX_VALIDATION_ISSUES = 20


def violates_unique_constraint(exc: IntegrityError, constraint: str) -> bool:
    """`IntegrityError` 가 그 이름의 unique 제약 위반인지. asyncpg 는 원인 예외에 제약 이름을 싣는다."""
    orig = exc.orig
    for holder in (getattr(orig, "diag", None), orig, getattr(orig, "__cause__", None)):
        name = getattr(holder, "constraint_name", None)
        if isinstance(name, str) and name:
            return name == constraint
    return constraint in str(orig)


def _validation_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {"loc": [str(part) for part in item.get("loc", ())], "type": item.get("type", "")}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(SemanticHTTPException)
    async def semantic_http_exc(request: Request, exc: SemanticHTTPException):
        if exc.status_code >= 500:
            logger.error(
                "semantic server failure",
                extra={
                    "error_status": exc.status_code,
                    "error_code": exc.code,
                    "error_diagnostic": exc.diagnostic_message,
                },
                exc_info=exc.__cause__,
            )
        return semantic_error_response_for(exc)

    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc: StarletteHTTPException):
        message = exc.detail if isinstance(exc.detail, str) else repr(exc.detail)
        if exc.status_code == 404:
            return semantic_error_response(
                code="resource_not_found",
                diagnostic_message=message,
                headers=exc.headers,
            )
        if exc.status_code == 405:
            return semantic_error_response(
                code="method_not_allowed",
                diagnostic_message=message,
                headers=exc.headers,
            )
        if exc.status_code == 400:
            # Starlette 가 요청 본문 파싱(깨진 multipart · part 수 초과)에서 내는 상태 — 클라이언트의 요청 형식 오류라
            # 검증 실패로 답한다. 서버 장애(internal_failure)로 보이면 안 된다
            return semantic_error_response(
                code="request_validation_failed",
                diagnostic_message=message,
                headers=exc.headers,
            )
        # product 코드는 SemanticHTTPException 만 내므로 여기 오는 다른 status 는 외부 의존성이 낸 것이다.
        logger.error("framework http failure", extra={"error_status": exc.status_code, "error_diagnostic": message})
        return semantic_error_response(
            code="internal_failure",
            diagnostic_message=f"HTTP {exc.status_code}: {message}",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exc(request: Request, exc: RequestValidationError):
        issues = [_validation_issue(item) for item in exc.errors() if isinstance(item, dict)]
        return semantic_error_response(
            code="request_validation_failed",
            details={"issues": issues[:MAX_VALIDATION_ISSUES]},
            diagnostic_message="Request validation failed",
        )

    @app.exception_handler(Exception)
    async def unhandled_exc(request: Request, exc: Exception):
        # ServerErrorMiddleware 는 request_context 미들웨어 바깥이라 ContextVar 가 이미 풀렸다.
        # 미들웨어가 scope state 에 남긴 값을 읽는다.
        request_id = request.scope.get("state", {}).get("request_id")
        logger.exception("unhandled request failure", extra={"request_id_at_failure": request_id})
        # 이 응답은 request_context 미들웨어의 send 를 거치지 않으므로 x-request-id 헤더도 여기서 붙인다.
        return semantic_error_response(
            code="internal_failure",
            request_id=request_id,
            headers={"x-request-id": request_id} if request_id else None,
        )
