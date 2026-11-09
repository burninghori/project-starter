/**
 * 오류 code 별 화면 문구 — backend 오류 code 목록(error-codes.generated.ts)과 짝을 이루는 단일 출처.
 *
 * `API_ERROR_MESSAGES` 는 `Record<ApiErrorCode, …>` 라 backend 에 code 가 추가되고(make gen-error-codes)
 * 여기 문구가 빠지면 TypeScript 컴파일이 실패한다. 화면은 문구를 직접 짓지 않고 `apiErrorMessage` 를 쓴다.
 *
 * 문구 규칙: 사용자가 할 수 있는 일을 한 문장으로. 마침표를 붙이지 않는다. details 에 값이 있으면 문장에 넣는다
 * (무엇이 걸렸는지 모르면 사용자가 고칠 수 없다). backend 원문(`diagnostic.message`)은 주 문구로 쓰지 않는다.
 */

import { formatDateTime } from "@/lib/format-date"

import { isPasswordRuleViolation, PASSWORD_RULE_MESSAGES, PASSWORD_RULE_SUMMARY } from "./auth/password-rules"
import type { ApiErrorCode } from "./error-codes.generated"
import { ApiError } from "./transport"

type ApiErrorPresenter = (error: ApiError) => string

function detailArray(error: ApiError, key: string): unknown[] {
  const value = error.details?.[key]
  return Array.isArray(value) ? value : []
}

/** 문장 뒤에 걸린 값을 괄호로 붙인다 — 값이 없으면 문장만 */
function withValue(message: string, value: unknown): string {
  return typeof value === "string" && value !== "" ? `${message} (${value})` : message
}

/** `auth_forbidden` 의 `details.required`(권한 이름) → 화면 이름. 모르는 값은 코드 값 그대로 보인다. 권한을 추가하면 여기 한 줄을 더한다 */
const REQUIRED_PERMISSION_LABELS: Record<string, string> = {
  admin: "관리자",
}

/** 바이트 → 「12.3MB」. 한도의 MB 는 1,048,576 바이트다(api.md 「업로드」 — 서버 검사와 같은 단위). 정수 MB 는 소수 없이 */
export function megabyteLabel(bytes: unknown): string | null {
  if (typeof bytes !== "number" || !Number.isFinite(bytes)) return null
  const mb = bytes / 1_048_576
  return `${Number.isInteger(mb) ? mb : mb.toFixed(1)}MB`
}

export const API_ERROR_MESSAGES: Record<ApiErrorCode, ApiErrorPresenter> = {
  // 공통
  resource_not_found: () => "요청한 대상을 찾을 수 없습니다. 이미 삭제됐는지 확인해 주세요",
  method_not_allowed: () => "지원하지 않는 요청입니다. 화면을 새로고침한 뒤 다시 시도해 주세요",
  request_validation_failed: (error) => {
    const count = detailArray(error, "issues").length
    return count > 0
      ? `입력값을 확인해 주세요 (${count}개 항목이 올바르지 않습니다)`
      : "입력값을 확인해 주세요"
  },
  request_origin_forbidden: () =>
    "허용되지 않은 주소에서 보낸 요청입니다. 서비스 주소로 직접 접속해 다시 시도해 주세요",
  internal_failure: () =>
    "서버에서 처리하지 못했습니다. 잠시 뒤 다시 시도하고, 계속되면 요청 ID 와 함께 알려 주세요",
  // 시스템
  database_unavailable: () => "데이터베이스에 연결할 수 없습니다. 잠시 뒤 다시 시도해 주세요",
  storage_unavailable: () => "파일 저장소에 연결할 수 없습니다. 잠시 뒤 다시 시도해 주세요",
  // 인증 — 아이디 없음과 비밀번호 틀림을 구분하지 않는다(계정이 있는지 알려 주지 않는다)
  auth_invalid_credentials: () => "아이디 또는 비밀번호가 맞지 않습니다",
  auth_required: () => "로그인이 필요합니다. 다시 로그인해 주세요",
  auth_user_inactive: () => "사용이 중지된 계정입니다. 관리자에게 문의하세요",
  auth_forbidden: (error) => {
    const required = error.details?.required
    const label = typeof required === "string" ? (REQUIRED_PERMISSION_LABELS[required] ?? required) : null
    return label === null
      ? "이 작업을 할 권한이 없습니다"
      : `이 작업을 할 권한이 없습니다 (필요한 권한: ${label})`
  },
  auth_password_change_required: () => "비밀번호를 먼저 바꿔야 다른 화면을 쓸 수 있습니다",
  auth_token_version_stale: () => "세션이 더 이상 유효하지 않습니다. 다시 로그인해 주세요",
  auth_password_rule_violation: (error) => {
    const rule = error.details?.rule
    return isPasswordRuleViolation(rule)
      ? PASSWORD_RULE_MESSAGES[rule]
      : `비밀번호 규칙에 맞지 않습니다 (${PASSWORD_RULE_SUMMARY})`
  },
  auth_current_password_invalid: () => "현재 비밀번호가 맞지 않습니다",
  auth_login_locked: (error) => {
    const until = error.details?.lockedUntil
    return typeof until === "string"
      ? `로그인 실패가 많아 계정이 잠겼습니다. ${formatDateTime(until)} 이후 다시 시도하거나 관리자에게 문의하세요`
      : "로그인 실패가 많아 계정이 잠겼습니다. 잠시 뒤 다시 시도하거나 관리자에게 문의하세요"
  },
  // 사용자 관리
  user_login_id_taken: (error) =>
    withValue("이미 있는 아이디입니다. 다른 아이디로 만들어 주세요", error.details?.loginId),
  user_last_admin_required: () =>
    "사용 중인 관리자가 이 계정 하나라 역할을 바꾸거나 사용을 중지할 수 없습니다. 다른 관리자를 먼저 지정하세요",
  user_self_change_forbidden: () =>
    "자기 계정의 역할 · 사용 여부는 바꿀 수 없고 비밀번호도 초기화할 수 없습니다. 다른 관리자에게 요청하세요",
  // 업로드 — 한도 값은 details 에 바이트로 오고 여기서 MB 로 바꾼다
  upload_length_required: () =>
    "업로드 요청에 길이 정보(Content-Length)가 없어 받을 수 없습니다. 화면에서 파일을 다시 올려 주세요",
  upload_file_name_invalid: (error) =>
    withValue(
      "쓸 수 없는 파일 이름입니다. 비어 있지 않고 255자 이하이며 제어 문자가 없는 이름으로 바꿔 올려 주세요",
      error.details?.fileName,
    ),
  upload_too_large: (error) => {
    const limit = megabyteLabel(error.details?.limit)
    const actual = megabyteLabel(error.details?.actual)
    const measured = actual === null ? "" : ` (${actual})`
    if (error.details?.scope === "file") {
      const name = error.details.fileName
      const subject = typeof name === "string" && name !== "" ? `${name} 이(가)` : "파일 하나가"
      return limit === null
        ? `${subject} 파일 한도를 넘습니다${measured}`
        : `${subject} 파일 한도 ${limit} 를 넘습니다${measured}`
    }
    return limit === null
      ? `선택한 파일의 합계가 요청 한도를 넘습니다${measured}. 나눠서 올려 주세요`
      : `선택한 파일의 합계가 요청 한도 ${limit} 를 넘습니다${measured}. 나눠서 올려 주세요`
  },
}

/** 목록에 없는 code(backend 가 더 새 버전)나 계약 밖 응답 — HTTP 상태로만 안내한다 */
function unknownErrorMessage(status: number): string {
  if (status >= 500) return "서버에서 처리하지 못했습니다. 잠시 뒤 다시 시도해 주세요"
  if (status === 404) return "요청한 대상을 찾을 수 없습니다"
  if (status === 401 || status === 403) return "이 작업을 할 권한이 없습니다"
  return "요청을 처리하지 못했습니다. 화면을 새로고침한 뒤 다시 시도해 주세요"
}

export const NETWORK_ERROR_MESSAGE =
  "서버에 연결하지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해 주세요"

/** 어떤 실패든 사용자에게 보일 한 문장. 토스트·오류 패널이 공통으로 쓴다. */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code === "unknown_error"
      ? unknownErrorMessage(error.status)
      : API_ERROR_MESSAGES[error.code](error)
  }
  return NETWORK_ERROR_MESSAGE
}

/** 폼 오류 한 줄(`FormError`)에 보일 것 — 문장과, 서버가 처리하지 못한 실패면 그 요청 ID */
export interface FormFailure {
  message: string
  requestId: string | null
}

/**
 * 실패를 폼 오류 한 줄로 바꾼다(app-ui-spec 5절 「입력」 — 폼 오류). 요청 ID 는 서버가 처리하지 못한 실패(5xx)에만 붙인다 —
 * 그 문구가 요청 ID 와 함께 알려 달라고 안내한다. 입력을 고쳐 넘어설 수 있는 실패(4xx)와 응답이 없는 실패(연결)는 null.
 */
export function formFailure(error: unknown): FormFailure {
  const requestId =
    error instanceof ApiError && error.status >= 500 && error.diagnostic !== null
      ? error.diagnostic.requestId
      : null
  return { message: apiErrorMessage(error), requestId }
}
