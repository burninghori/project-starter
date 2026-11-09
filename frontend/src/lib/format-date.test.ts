import { describe, expect, it } from "vitest"

import { formatDate, formatDateTime, formatDateTimeSeconds } from "./format-date"

// 브라우저 시간대로 보이므로, 기대값도 같은 시간대의 시각에서 만든다(테스트가 도는 시간대와 무관하게)
const AT = new Date(2026, 9, 28, 14, 5, 9).toISOString()

describe("format-date", () => {
  it("목록은 날짜만, 이력 일시는 분까지, 올리면 초까지 — 한 자리는 0 을 채운다", () => {
    expect(formatDate(AT)).toBe("2026-10-28")
    expect(formatDateTime(AT)).toBe("2026-10-28 14:05")
    expect(formatDateTimeSeconds(AT)).toBe("2026-10-28 14:05:09")
  })

  it("시각이 아닌 값은 빈 글자로 바꾸지 않고 던진다", () => {
    expect(() => formatDate("언젠가")).toThrow("시각 문자열이 아니다")
  })
})
