/**
 * 페이지 나눔 계산 — 화면 상태와 무관한 순수 함수.
 * 목록이 바뀌면(필터·정렬) 1쪽으로, 쪽 크기만 바뀌면 보던 위치가 들어 있는 쪽으로 간다.
 */

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

/** 셀렉트 값(문자열)을 쪽 크기로 — 선택지 밖의 값이면 오류(기조 5: 경계에서 한 번 검증) */
export function toPageSize(raw: string): PageSize {
  const size = PAGE_SIZE_OPTIONS.find((option) => String(option) === raw)
  if (size === undefined) throw new Error(`지원하지 않는 쪽 크기: ${raw}`)
  return size
}

export interface PageWindow {
  /** 1부터. 전체가 0건이어도 1 */
  page: number
  pageCount: number
  /** 이 쪽에 보이는 첫 행 번호(1부터). 0건이면 0 */
  first: number
  /** 이 쪽에 보이는 마지막 행 번호. 0건이면 0 */
  last: number
}

/** `page` 가 범위를 넘으면 마지막 쪽으로 붙인다(필터로 건수가 줄어든 경우) */
export function pageWindow(page: number, pageSize: number, total: number): PageWindow {
  if (!Number.isInteger(page) || page < 1) throw new Error(`page 는 1 이상의 정수여야 한다: ${page}`)
  if (!Number.isInteger(pageSize) || pageSize < 1)
    throw new Error(`pageSize 는 1 이상의 정수여야 한다: ${pageSize}`)
  if (!Number.isInteger(total) || total < 0) throw new Error(`total 은 0 이상의 정수여야 한다: ${total}`)
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const current = Math.min(page, pageCount)
  const start = (current - 1) * pageSize
  return {
    page: current,
    pageCount,
    first: total === 0 ? 0 : start + 1,
    last: Math.min(total, start + pageSize),
  }
}

/** 쪽 크기를 바꿀 때 — 보던 쪽의 첫 행이 들어 있는 새 쪽 번호 */
export function pageAfterResize(page: number, oldSize: number, newSize: number): number {
  const firstRow = (page - 1) * oldSize + 1
  return Math.max(1, Math.ceil(firstRow / newSize))
}
