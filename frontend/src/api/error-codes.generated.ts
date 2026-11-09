// 자동 생성 — backend/scripts/generate_error_codes.py 가 backend/app/api/error_contract.py 에서 만든다.
// 손으로 고치지 않는다. 다시 만들기: make gen-error-codes

export const API_ERROR_CONTRACT_VERSION = "semantic-v1"

export type ApiErrorFamily =
  | "bad_request"
  | "authentication"
  | "authorization"
  | "not_found"
  | "conflict"
  | "validation"
  | "payload_too_large"
  | "too_many_requests"
  | "unavailable"
  | "internal"

export type ApiErrorCode =
  | "resource_not_found"
  | "method_not_allowed"
  | "request_validation_failed"
  | "request_origin_forbidden"
  | "internal_failure"
  | "database_unavailable"
  | "storage_unavailable"
  | "auth_invalid_credentials"
  | "auth_required"
  | "auth_user_inactive"
  | "auth_forbidden"
  | "auth_password_change_required"
  | "auth_token_version_stale"
  | "auth_password_rule_violation"
  | "auth_current_password_invalid"
  | "auth_login_locked"
  | "user_login_id_taken"
  | "user_self_change_forbidden"
  | "user_last_admin_required"
  | "upload_length_required"
  | "upload_file_name_invalid"
  | "upload_too_large"

export const API_ERROR_CODES: readonly ApiErrorCode[] = [
  "resource_not_found",
  "method_not_allowed",
  "request_validation_failed",
  "request_origin_forbidden",
  "internal_failure",
  "database_unavailable",
  "storage_unavailable",
  "auth_invalid_credentials",
  "auth_required",
  "auth_user_inactive",
  "auth_forbidden",
  "auth_password_change_required",
  "auth_token_version_stale",
  "auth_password_rule_violation",
  "auth_current_password_invalid",
  "auth_login_locked",
  "user_login_id_taken",
  "user_self_change_forbidden",
  "user_last_admin_required",
  "upload_length_required",
  "upload_file_name_invalid",
  "upload_too_large",
]

export const API_ERROR_STATUS: Record<ApiErrorCode, number> = {
  resource_not_found: 404,
  method_not_allowed: 405,
  request_validation_failed: 422,
  request_origin_forbidden: 403,
  internal_failure: 500,
  database_unavailable: 503,
  storage_unavailable: 503,
  auth_invalid_credentials: 401,
  auth_required: 401,
  auth_user_inactive: 403,
  auth_forbidden: 403,
  auth_password_change_required: 403,
  auth_token_version_stale: 409,
  auth_password_rule_violation: 422,
  auth_current_password_invalid: 422,
  auth_login_locked: 429,
  user_login_id_taken: 409,
  user_self_change_forbidden: 409,
  user_last_admin_required: 409,
  upload_length_required: 411,
  upload_file_name_invalid: 422,
  upload_too_large: 413,
}
