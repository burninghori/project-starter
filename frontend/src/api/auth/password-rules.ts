/**
 * 비밀번호 규칙 — 정본은 backend `app/domains/auth/passwords.py` 이고 여기는 같은 값으로 입력을 미리 검사한다.
 * 값을 바꾸면 양쪽을 함께 바꾼다. 규칙: 8자 이상 · UTF-8 72바이트 이하 · 공백·줄바꿈 금지 · 조합 요구 없음.
 */

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_BYTES = 72

export type PasswordRuleViolation = "too_short" | "too_long" | "whitespace"

/** 규칙마다 「어겼는가」. 글자 수는 코드 포인트 기준(backend len())이다 — UTF-16 단위(.length)가 아니다 */
const VIOLATED: Record<PasswordRuleViolation, (raw: string) => boolean> = {
  too_short: (raw) => [...raw].length < PASSWORD_MIN_LENGTH,
  too_long: (raw) => new TextEncoder().encode(raw).length > PASSWORD_MAX_BYTES,
  whitespace: (raw) => /\s/u.test(raw),
}

/** backend 와 같은 검사 순서 */
const CHECK_ORDER: readonly PasswordRuleViolation[] = ["too_short", "too_long", "whitespace"]

export const PASSWORD_RULE_MESSAGES: Record<PasswordRuleViolation, string> = {
  too_short: `비밀번호는 ${PASSWORD_MIN_LENGTH}자 이상이어야 합니다`,
  too_long: `비밀번호가 너무 깁니다 (영문·숫자 ${PASSWORD_MAX_BYTES}자, 한글 ${Math.floor(PASSWORD_MAX_BYTES / 3)}자 이하)`,
  whitespace: "비밀번호에 공백이나 줄바꿈을 쓸 수 없습니다",
}

/**
 * 규칙 한 줄 안내 — 새 비밀번호 칸 아래에 입력 전부터 보이고, 오류 응답의 규칙 값을 모를 때의 안내에도 쓴다.
 * 흔히 쓰는 「공백 없이 8자 이상」 표기에 조합이 필요 없다는 것을 덧붙인다.
 * 72바이트 상한은 거의 닿지 않아 안내에 두지 않고, 넘으면 오류로 알린다.
 */
export const PASSWORD_RULE_SUMMARY = `공백 없이 ${PASSWORD_MIN_LENGTH}자 이상. 영문·숫자·특수문자 조합은 필요 없습니다`

/** 규칙을 어기면 그 사유, 맞으면 null. backend 와 같은 순서로 검사한다 */
export function passwordRuleViolation(raw: string): PasswordRuleViolation | null {
  return CHECK_ORDER.find((rule) => VIOLATED[rule](raw)) ?? null
}

/** 오류 응답 `details.rule` 이 아는 값인지 — 모르는 값이면 화면은 규칙 요약으로 안내한다 */
export function isPasswordRuleViolation(value: unknown): value is PasswordRuleViolation {
  return typeof value === "string" && (CHECK_ORDER as readonly string[]).includes(value)
}
