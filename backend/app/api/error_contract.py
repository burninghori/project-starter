"""HTTP 오류 응답 계약(semantic-v1) — 오류 code 목록과 code → HTTP 상태 표의 단일 출처.

backend 는 "무슨 일이 있었고 값이 무엇인지" 를 정하고, 화면이 "어떤 문구로 보여줄지" 를 정한다.
그래서 응답에는 사용자 문장을 싣지 않는다. 화면은 `code`·`details` 로 문구를 만들고(frontend
`src/api/error-messages.ts`), `diagnostic.message` 는 개발·지원용 원문이다.

wire 형태:

    {"error": {"contract": "semantic-v1", "family": "not_found", "code": "resource_not_found",
               "details": {...}, "diagnostic": {"message": "...", "requestId": "..."}}}

새 code 를 추가하는 법(backend-conventions skill 「오류」):

1. 아래 `ApiErrorCode` 와 `ERROR_CODE_STATUS` 에 한 줄씩 더한다(둘이 어긋나면 import 시 실패).
2. `make gen-error-codes` 로 frontend 타입(`src/api/error-codes.generated.ts`)을 다시 만든다.
3. frontend `src/api/error-messages.ts` 에 문구를 더한다(빠지면 TypeScript 컴파일 에러).

product 코드는 `SemanticHTTPException` 하나로 오류를 낸다. FastAPI 의 `HTTPException` 은 쓰지 않는다.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Literal, get_args

from starlette.responses import JSONResponse

from ..context import get_request_id

ERROR_CONTRACT_VERSION: Literal["semantic-v1"] = "semantic-v1"

ApiErrorFamily = Literal[
    "bad_request",
    "authentication",
    "authorization",
    "not_found",
    "conflict",
    "validation",
    "payload_too_large",
    "too_many_requests",
    "unavailable",
    "internal",
]

# HTTP 상태 하나는 family 하나에만 대응한다.
FAMILY_BY_STATUS: Mapping[int, ApiErrorFamily] = MappingProxyType(
    {
        400: "bad_request",
        401: "authentication",
        403: "authorization",
        404: "not_found",
        405: "bad_request",
        409: "conflict",
        411: "bad_request",
        413: "payload_too_large",
        422: "validation",
        429: "too_many_requests",
        500: "internal",
        502: "unavailable",
        503: "unavailable",
    }
)

# 오류 code 목록. 이름은 `<대상>_<사유>` snake_case 이고, 도메인별로 묶어 둔다.
# 목록에 없는 code 로 오류를 내면 pyright 가 잡는다.
ApiErrorCode = Literal[
    # 공통 — 프레임워크·요청 형식·서버
    "resource_not_found",
    "method_not_allowed",
    "request_validation_failed",
    "request_origin_forbidden",
    "internal_failure",
    # 시스템
    "database_unavailable",
    "storage_unavailable",
    # 인증 (api.md 「인증」)
    "auth_invalid_credentials",
    "auth_required",
    "auth_user_inactive",
    "auth_forbidden",
    "auth_password_change_required",
    "auth_token_version_stale",
    "auth_password_rule_violation",
    "auth_current_password_invalid",
    "auth_login_locked",
    # 사용자 관리 (api.md 「사용자 관리」)
    "user_login_id_taken",
    "user_self_change_forbidden",
    "user_last_admin_required",
    # 업로드 공통 (api.md 「업로드」, app/api/uploads.py)
    "upload_length_required",
    "upload_file_name_invalid",
    "upload_too_large",
]

# code 하나는 HTTP 상태 하나에만 대응한다. 상태와 family 는 code 가 정하므로 호출부가 따로 넘기지 않는다.
ERROR_CODE_STATUS: Mapping[ApiErrorCode, int] = MappingProxyType(
    {
        "resource_not_found": 404,
        "method_not_allowed": 405,
        "request_validation_failed": 422,
        "request_origin_forbidden": 403,
        "internal_failure": 500,
        "database_unavailable": 503,
        "storage_unavailable": 503,
        "auth_invalid_credentials": 401,
        "auth_required": 401,
        "auth_user_inactive": 403,
        "auth_forbidden": 403,
        "auth_password_change_required": 403,
        "auth_token_version_stale": 409,
        "auth_password_rule_violation": 422,
        "auth_current_password_invalid": 422,
        "auth_login_locked": 429,
        "user_login_id_taken": 409,
        "user_self_change_forbidden": 409,
        "user_last_admin_required": 409,
        "upload_length_required": 411,
        "upload_file_name_invalid": 422,
        "upload_too_large": 413,
    }
)

if set(ERROR_CODE_STATUS) != set(get_args(ApiErrorCode)):  # pragma: no cover - import 시점 계약
    raise RuntimeError("ApiErrorCode 목록과 ERROR_CODE_STATUS 표가 다르다")
if unknown := {status for status in ERROR_CODE_STATUS.values() if status not in FAMILY_BY_STATUS}:  # pragma: no cover
    raise RuntimeError(f"FAMILY_BY_STATUS 에 없는 HTTP 상태: {sorted(unknown)}")

MAX_DIAGNOSTIC_CHARS = 1000


def error_status(code: ApiErrorCode) -> int:
    return ERROR_CODE_STATUS[code]


def error_family(code: ApiErrorCode) -> ApiErrorFamily:
    return FAMILY_BY_STATUS[ERROR_CODE_STATUS[code]]


class SemanticHTTPException(Exception):  # noqa: N818 — 이름 자체가 계약이라 Error 접미어를 붙이지 않는다
    """product 코드가 내는 유일한 HTTP 오류.

    `code` 는 `ApiErrorCode` 목록의 값이다. HTTP 상태와 family 는 code 가 정한다.
    `details` 는 화면이 문구를 만들 때 쓰는 값만 camelCase 키로 담는다.
    `diagnostic_message` 는 원인 원문이다. 비밀 값을 넣지 않는다.

        raise SemanticHTTPException(code="resource_not_found", details={"resource": "user", "id": user_id})
    """

    def __init__(
        self,
        *,
        code: ApiErrorCode,
        details: dict[str, Any] | None = None,
        diagnostic_message: str | None = None,
    ) -> None:
        super().__init__(f"HTTP {error_status(code)} · {code}")
        self.code: ApiErrorCode = code
        self.status_code = error_status(code)
        self.family: ApiErrorFamily = error_family(code)
        self.details = details
        self.diagnostic_message = diagnostic_message


def render_error_envelope(
    *,
    code: ApiErrorCode,
    details: dict[str, Any] | None,
    diagnostic_message: str | None,
    request_id: str | None = None,
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {"requestId": request_id or get_request_id()}
    if diagnostic_message:
        diagnostic["message"] = diagnostic_message[:MAX_DIAGNOSTIC_CHARS]
    body: dict[str, Any] = {"contract": ERROR_CONTRACT_VERSION, "family": error_family(code), "code": code}
    if details is not None:
        body["details"] = details
    body["diagnostic"] = diagnostic
    return {"error": body}


def semantic_error_response(
    *,
    code: ApiErrorCode,
    details: dict[str, Any] | None = None,
    diagnostic_message: str | None = None,
    request_id: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=error_status(code),
        content=render_error_envelope(
            code=code, details=details, diagnostic_message=diagnostic_message, request_id=request_id
        ),
        headers=headers,
    )


def semantic_error_response_for(exc: SemanticHTTPException, *, request_id: str | None = None) -> JSONResponse:
    return semantic_error_response(
        code=exc.code, details=exc.details, diagnostic_message=exc.diagnostic_message, request_id=request_id
    )
