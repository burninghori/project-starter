/**
 * 서버 시각(ISO 8601 UTC 문자열)의 화면 표기 — CLAUDE.md 「날짜 표기」: 목록은 `YYYY-MM-DD`, 이력 일시는
 * `YYYY-MM-DD HH:mm`, 마우스를 올리면 초까지. 브라우저 시간대로 보인다. `MM/DD` 는 해를 넘기는 구간에서 헷갈려 쓰지 않는다.
 * 계약 밖의 값(파싱되지 않는 문자열)은 빈 글자나 「-」로 바꾸지 않고 던진다(기조 5).
 */

function parse(iso: string): Date {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) throw new Error(`시각 문자열이 아니다: ${iso}`)
  return date
}

const two = (value: number) => String(value).padStart(2, "0")

function datePart(date: Date): string {
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`
}

function timePart(date: Date): string {
  return `${two(date.getHours())}:${two(date.getMinutes())}`
}

/** 「2026-10-28」 */
export function formatDate(iso: string): string {
  return datePart(parse(iso))
}

/** 「2026-10-28 14:05」 */
export function formatDateTime(iso: string): string {
  const date = parse(iso)
  return `${datePart(date)} ${timePart(date)}`
}

/** 「2026-10-28 14:05:09」 — 일시 위에 마우스를 올렸을 때(`title`) */
export function formatDateTimeSeconds(iso: string): string {
  const date = parse(iso)
  return `${datePart(date)} ${timePart(date)}:${two(date.getSeconds())}`
}
