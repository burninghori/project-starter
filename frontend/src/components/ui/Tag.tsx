import type { MouseEvent, ReactNode } from "react"

import { cn } from "@/lib/cn"

/**
 * 상태 태그의 색 — 뜻은 design-concept 3절, 대상별 매핑은 app-ui-spec 6절.
 * `system` 은 결과 축 밖의 시스템 상태(예: 「미수행」)로, 회색에 점선 테두리다.
 */
export type TagTone = "ok" | "warn" | "danger" | "neutral" | "system"

/** 상태를 짧게 보이는 알약. **상태에만** 쓴다 — 분류·속성은 `app-plain` 글자로 둔다 */
export function Tag({ tone, children }: { tone: TagTone; children: ReactNode }) {
  return (
    <span
      className={cn("app-tag", tone === "system" ? "app-tag--neutral app-tag--dashed" : `app-tag--${tone}`)}
    >
      {children}
    </span>
  )
}

/**
 * 상태 태그 + mono ID 를 한 버튼으로 — ID 가 곧 이동 버튼이다(표의 ID 열 등, design-concept 2절 「근거로 바로 간다」).
 * 태그만으로 상태가 보이므로 ID 만 두지 않는다. 누르는 줄 안에 둘 때는 `onClick` 이 받은 이벤트의 전파를 막는다(줄이 같이 눌리지 않게).
 */
export function TagIdButton({
  tone,
  status,
  id,
  onClick,
}: {
  tone: TagTone
  status: string
  id: string
  onClick: (event: MouseEvent<HTMLButtonElement>) => void
}) {
  return (
    <button type="button" className="app-btn app-btn--sm app-idbtn" onClick={onClick}>
      <Tag tone={tone}>{status}</Tag> <span className="app-mono">{id}</span>
    </button>
  )
}

/**
 * 결과를 크게 보일 때의 상태 글자 — 굵은 글자에 상태색(design-concept 3절 5번). 크기는 놓이는 자리가 정한다
 * (스텝 카드 19px · 요약 18px 등). 시스템 상태(`system`)는 큰 글자에서도 회색이다.
 */
export function StatusText({ tone, children }: { tone: TagTone; children: ReactNode }) {
  return (
    <span className={cn("app-status", `app-status--${tone === "system" ? "neutral" : tone}`)}>
      {children}
    </span>
  )
}
