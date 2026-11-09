import { useEffect, useRef, type KeyboardEvent, type ReactNode } from "react"

import { cn } from "@/lib/cn"

/**
 * 표의 작은 조각. 표 자체는 `<table className="app-table">` 를 `app-table-wrap` 안에 직접 쓴다 —
 * 열 구성이 화면마다 달라 표 전체를 감싸는 컴포넌트를 두지 않는다. 클래스 쓰임은 app-ui-spec 5절 「목록 도구」:
 *   숫자 열 `app-table__num` · 상태·버튼 열 `app-table__center` · 선택 행 `aria-selected` ·
 *   그룹 행 `app-table__group` · 하위 행 `app-table__child` · 접기 표시 `ExpandMark` · 선택 체크 `app-table__check`
 */

/** 조건에 맞는 행이 없을 때의 한 줄. 데이터를 아직 못 가져온 자리에는 쓰지 않는다(그건 PendingContract) */
export function TableEmptyRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="app-table__empty">
        {children}
      </td>
    </tr>
  )
}

/**
 * 펼치는 줄의 제목 바로 앞 표시 — 채운 삼각형, 접혀 있으면 오른쪽 · 펼쳐 있으면 아래(같은 삼각형을 돌린다). 모양은 CSS 가 그린다
 * (`app-table__toggle` — app-ui-spec 8절 D66). 장식이다 — 펼침은 그 행의 `aria-expanded` 가 알린다
 */
export function ExpandMark({ open }: { open: boolean }) {
  return <span className={cn("app-table__toggle", open && "app-table__toggle--open")} aria-hidden />
}

/**
 * 선택 행의 제목 앞 표시(청록 채운 삼각형, `app-table__mark`). 고르지 않은 행도 같은 자리를 비워 둔다 — 고를 때 그 행의 글자가
 * 옆으로 밀리지 않게. 장식이다 — 선택은 그 행의 `aria-selected` 가 알린다
 */
export function SelectedMark({ selected }: { selected: boolean }) {
  return <span className={cn("app-table__mark", !selected && "app-table__mark--off")} aria-hidden />
}

/**
 * 표 행 전체가 버튼인 경우(줄 선택 · 그룹 접기 · 줄 펼치기)의 키보드 동작 — 행에 포커스가 있을 때 Enter · Space 가 클릭과 같다.
 * 행 안의 버튼 · 체크에서 올라온 키는 건드리지 않는다 — 막으면 그 버튼이 키보드로 눌리지 않고 행이 대신 눌린다.
 */
export function rowKeyHandler(action: () => void) {
  return (event: KeyboardEvent<HTMLTableRowElement>) => {
    if (event.target !== event.currentTarget) return
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault()
      action()
    }
  }
}

/**
 * 선택 열의 머리 체크(app-ui-spec 5절 「체크박스」) — 이 쪽의 고를 수 있는 행 전부를 고르거나 푼다. 일부만 골랐으면 일부 선택
 * (`indeterminate` — HTML 속성이 없어 DOM 에 직접 단다). 고를 수 있는 행이 없으면 비활성.
 */
export function SelectAllCheckbox({
  label,
  state,
  disabled,
  onChange,
}: {
  /** 접근성 이름 — 무엇을 고르는지(「이 쪽의 항목 모두 선택」) */
  label: string
  state: "all" | "some" | "none"
  disabled: boolean
  onChange: (checked: boolean) => void
}) {
  const ref = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (ref.current !== null) ref.current.indeterminate = state === "some"
  }, [state])
  return (
    <input
      ref={ref}
      type="checkbox"
      className="app-table__check"
      aria-label={label}
      checked={state === "all"}
      disabled={disabled}
      onChange={(event) => onChange(event.target.checked)}
    />
  )
}

/** 선택 열의 행 체크. 고를 수 없는 행은 체크 대신 회색 「-」(`SelectNone`) */
export function RowCheckbox({
  label,
  checked,
  onChange,
}: {
  /** 접근성 이름 — 그 행이 무엇인지(「ORD-0012 선택」) */
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
}) {
  return (
    <input
      type="checkbox"
      className="app-table__check"
      aria-label={label}
      checked={checked}
      onChange={(event) => onChange(event.target.checked)}
      // 행이 누르면 펼쳐지는 행이어도 체크는 체크만 한다
      onClick={(event) => event.stopPropagation()}
    />
  )
}

/** 고를 수 없는 행의 선택 칸 표시 */
export function SelectNone() {
  return <span className="app-zero">-</span>
}
