/**
 * 목록 API 의 공용 응답(api.md 「공통 규칙」) — `rows` 는 요청한 쪽의 행, `total` 은 필터 적용 후·쪽 자르기 전 전체 건수,
 * `pageCount` 는 마지막 쪽 번호(0건이면 0). 도메인 모듈이 행 타입을 넣어 쓴다.
 */
export interface PageEnvelope<Row> {
  rows: Row[]
  total: number
  pageCount: number
}
