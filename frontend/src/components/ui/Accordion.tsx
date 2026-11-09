import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

import { Button } from "./Button"

/**
 * 펼친 줄 패널(아코디언) — 표의 줄을 누르면 그 바로 아래에 붙는 안쪽 패널(app-ui-spec 5절 「목록 도구」).
 * 오른쪽 상자(「이름 · 값」 줄들)는 있어도 없어도 된다. 줄의 펼침 상태는 `use-expanded-rows` 가 맡는다.
 */

/** 펼친 줄 바로 아래 행 — 칸 전체를 쓰고 바탕이 회색이라 위 줄에 딸린 것으로 보인다 */
export function AccordionRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr className="app-acc-row">
      <td colSpan={colSpan}>{children}</td>
    </tr>
  )
}

/**
 * 안쪽 패널 — 머리(제목 + 건수 + 오른쪽 끝 동작 · 안내)와 본문(표 하나, 또는 표 대신 안내 한 줄), 있으면 오른쪽 상자.
 * 오른쪽 상자가 있으면 `app-acc--side` 를 붙인다 — 본문 표의 칸 폭을 줄일 때 이 이름으로 건다.
 */
export function AccordionPanel({
  title,
  count,
  actions,
  side,
  children,
}: {
  title: string
  /** 머리 제목 옆 「n건」. 셀 수 없으면(지금 결과가 없음) null */
  count: number | null
  /** 머리 오른쪽 끝의 단추 · 안내 글자. 없으면 null */
  actions: ReactNode
  /** 오른쪽 상자(`AccordionSide`). 없으면 null */
  side: ReactNode
  children: ReactNode
}) {
  return (
    <div className={cn("app-acc", side !== null && "app-acc--side")}>
      <div className="min-w-0 flex-1">
        <div className="app-acc__head">
          <span>{title}</span>
          {count !== null && <span className="app-acc__count">{count.toLocaleString()}건</span>}
          {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
        </div>
        {children}
      </div>
      {side}
    </div>
  )
}

/** 패널 본문 자리에 표 대신 두는 안내 한 줄(지금 결과가 없을 때 등) */
export function AccordionNote({ children }: { children: ReactNode }) {
  return <p className="app-acc__note">{children}</p>
}

/** 오른쪽 상자 — 「이름 · 값」 줄들(예: 등록일 · 처리일 · 처리 결과) */
export function AccordionSide({ items }: { items: readonly { label: string; value: ReactNode }[] }) {
  return (
    <dl className="app-acc__side">
      {items.map((item) => (
        <div key={item.label} className="contents">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

/**
 * 「모두 펼치기 / 모두 접기」 — 이 쪽의 줄만 대상이다. 이 쪽의 줄이 모두 펼쳐져 있으면 「모두 접기」로 바뀐다.
 * 줄이 없으면 비활성.
 */
export function ExpandAllButton({
  allOpen,
  disabled,
  onToggle,
}: {
  allOpen: boolean
  disabled: boolean
  onToggle: () => void
}) {
  return (
    <Button variant="secondary" size="md" disabled={disabled} onClick={onToggle}>
      {allOpen ? "모두 접기" : "모두 펼치기"}
    </Button>
  )
}
