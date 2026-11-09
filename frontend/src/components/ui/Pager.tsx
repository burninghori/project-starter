import { Button } from "./Button"
import { PAGE_SIZE_OPTIONS, pageAfterResize, pageWindow, toPageSize, type PageSize } from "./pager-math"

interface PagerProps {
  page: number
  pageSize: PageSize
  total: number
  onPageChange: (page: number) => void
  /** 쪽 크기를 바꾸면 보던 위치가 들어 있는 쪽으로 함께 옮긴다 */
  onPageSizeChange: (pageSize: PageSize, page: number) => void
}

/**
 * 긴 표 아래의 페이지 나눔 — 「1–10 표시」 · 「10건씩」 · 이전 · n / N · 다음.
 * 표를 감싼 카드·`app-table-wrap` 바로 아래에 둔다.
 */
export function Pager({ page, pageSize, total, onPageChange, onPageSizeChange }: PagerProps) {
  const view = pageWindow(page, pageSize, total)
  return (
    <div className="app-pager flex flex-wrap items-center gap-2">
      <span className="app-num">
        {view.first}–{view.last} 표시
      </span>
      <select
        className="app-pager__size ml-2.5"
        aria-label="표시 건수"
        value={pageSize}
        onChange={(event) => {
          const next = toPageSize(event.target.value)
          onPageSizeChange(next, pageAfterResize(view.page, pageSize, next))
        }}
      >
        {PAGE_SIZE_OPTIONS.map((size) => (
          <option key={size} value={size}>
            {size}건씩
          </option>
        ))}
      </select>
      <span className="flex-1" />
      <Button
        variant="secondary"
        size="sm"
        disabled={view.page <= 1}
        onClick={() => onPageChange(view.page - 1)}
      >
        이전
      </Button>
      <span className="app-num mx-1.5" aria-label={`${view.pageCount}쪽 중 ${view.page}쪽`}>
        {view.page} / {view.pageCount}
      </span>
      <Button
        variant="secondary"
        size="sm"
        disabled={view.page >= view.pageCount}
        onClick={() => onPageChange(view.page + 1)}
      >
        다음
      </Button>
    </div>
  )
}
