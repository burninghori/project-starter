import { describe, expect, it } from "vitest"

import { API_ERROR_CODES } from "./error-codes.generated"
import {
  API_ERROR_MESSAGES,
  apiErrorMessage,
  formFailure,
  megabyteLabel,
  NETWORK_ERROR_MESSAGE,
} from "./error-messages"
import { ApiError } from "./transport"

describe("apiErrorMessage", () => {
  it.each(API_ERROR_CODES)("%s 에 문구가 있다", (code) => {
    const message = API_ERROR_MESSAGES[code](new ApiError(400, null, code, undefined, null))

    expect(message.length).toBeGreaterThan(0)
    expect(message.endsWith(".")).toBe(false)
  })

  it("잠긴 계정은 풀리는 시각을 문장에 넣는다", () => {
    const error = new ApiError(
      429,
      "too_many_requests",
      "auth_login_locked",
      { lockedUntil: "2026-01-02T03:04:05+00:00" },
      null,
    )

    expect(apiErrorMessage(error)).toContain("이후 다시 시도")
  })

  it("details 의 값을 문장에 넣는다", () => {
    const error = new ApiError(422, "validation", "request_validation_failed", { issues: [{}, {}] }, null)

    expect(apiErrorMessage(error)).toContain("2개 항목")
  })

  it("업로드 한도는 바이트를 MB 로 바꿔 넣고, 파일 한도면 파일 이름을 앞세운다", () => {
    const tooLarge = (details: Record<string, unknown>) =>
      apiErrorMessage(new ApiError(413, "payload_too_large", "upload_too_large", details, null))

    expect(tooLarge({ scope: "file", fileName: "report.pdf", limit: 104_857_600, actual: 115_343_360 })).toBe(
      "report.pdf 이(가) 파일 한도 100MB 를 넘습니다 (110MB)",
    )
    expect(tooLarge({ scope: "request", limit: 314_572_800, actual: 330_301_440 })).toBe(
      "선택한 파일의 합계가 요청 한도 300MB 를 넘습니다 (315MB). 나눠서 올려 주세요",
    )
    expect(megabyteLabel(1_153_433)).toBe("1.1MB")
    expect(megabyteLabel("x")).toBeNull()
  })

  it("권한 부족 — 필요한 권한을 화면 이름으로, 모르는 권한은 코드 값 그대로", () => {
    const forbidden = (required: string) =>
      apiErrorMessage(new ApiError(403, "authorization", "auth_forbidden", { required }, null))

    expect(forbidden("admin")).toBe("이 작업을 할 권한이 없습니다 (필요한 권한: 관리자)")
    expect(forbidden("can_export")).toBe("이 작업을 할 권한이 없습니다 (필요한 권한: can_export)")
  })

  it("목록에 없는 code 는 HTTP 상태로 안내한다", () => {
    const error = new ApiError(503, null, "unknown_error", undefined, null, "brand_new_code")

    expect(apiErrorMessage(error)).toContain("서버에서 처리하지 못했습니다")
    expect(error.message).toBe("HTTP 503 · brand_new_code")
  })

  it("응답이 없는 실패는 연결 문구", () => {
    expect(apiErrorMessage(new TypeError("Failed to fetch"))).toBe(NETWORK_ERROR_MESSAGE)
  })
})

describe("formFailure", () => {
  it("서버가 처리하지 못한 실패(5xx)에만 요청 ID 를 붙인다", () => {
    const serverFailure = new ApiError(500, "internal", "internal_failure", undefined, { requestId: "req-5" })
    const conflict = new ApiError(409, "conflict", "auth_current_password_invalid", undefined, {
      requestId: "req-4",
    })

    expect(formFailure(serverFailure)).toEqual({
      message: apiErrorMessage(serverFailure),
      requestId: "req-5",
    })
    // 입력을 고쳐 넘어설 수 있는 실패와 응답이 없는 실패에는 붙이지 않는다
    expect(formFailure(conflict).requestId).toBeNull()
    expect(formFailure(new TypeError("Failed to fetch"))).toEqual({
      message: NETWORK_ERROR_MESSAGE,
      requestId: null,
    })
    // 요청 ID 를 받지 못한 5xx(계약 밖 응답)는 붙일 값이 없다
    expect(formFailure(new ApiError(502, null, "unknown_error", undefined, null)).requestId).toBeNull()
  })
})
