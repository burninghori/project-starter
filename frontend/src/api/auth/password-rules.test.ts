import { describe, expect, it } from "vitest"

import { isPasswordRuleViolation, passwordRuleViolation } from "./password-rules"

// 「가」는 UTF-8 3바이트 — 24자가 정확히 72바이트
const HANGUL_72_BYTES = "가".repeat(24)

describe("passwordRuleViolation", () => {
  it.each([
    ["a".repeat(7), "too_short"],
    ["a".repeat(8), null],
    ["가".repeat(7), "too_short"],
    ["가".repeat(8), null],
    ["a".repeat(72), null],
    ["a".repeat(73), "too_long"],
    [HANGUL_72_BYTES, null],
    [`${HANGUL_72_BYTES}a`, "too_long"],
    [" abcdefgh", "whitespace"],
    ["abcdefgh ", "whitespace"],
    ["abcd efgh", "whitespace"],
    ["abcd\nefgh", "whitespace"],
    ["12345678", null],
  ] as const)("%j → %s", (raw, expected) => {
    expect(passwordRuleViolation(raw)).toBe(expected)
  })
})

describe("isPasswordRuleViolation", () => {
  it("아는 값만 참", () => {
    expect(isPasswordRuleViolation("too_short")).toBe(true)
    expect(isPasswordRuleViolation("brand_new_rule")).toBe(false)
    expect(isPasswordRuleViolation(undefined)).toBe(false)
  })
})
