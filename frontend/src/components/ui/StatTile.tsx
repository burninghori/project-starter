import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

/** 값의 색 — 상태색은 값에만 쓰고 타일 바탕에는 쓰지 않는다(design-concept 3절) */
export type StatTone = "plain" | "ok" | "warn" | "danger"

interface StatContentProps {
  label: string
  value: number
  /** 값 아래 보조 줄. 없으면 null */
  sub: ReactNode
  tone: StatTone
  size: "md" | "sm"
}

function statClass(tone: StatTone, size: "md" | "sm") {
  return cn("app-stat", size === "sm" && "app-stat--sm", tone !== "plain" && `app-stat--${tone}`)
}

function StatContent({ label, value, sub }: Pick<StatContentProps, "label" | "value" | "sub">) {
  return (
    <>
      <div className="app-stat__label">{label}</div>
      <div className="app-stat__value">{value.toLocaleString()}</div>
      {sub !== null && <div className="app-stat__sub">{sub}</div>}
    </>
  )
}

/** 요약 수치 한 칸(보기 전용) */
export function StatTile({ label, value, sub, tone, size }: StatContentProps) {
  return (
    <div className={statClass(tone, size)}>
      <StatContent label={label} value={value} sub={sub} />
    </div>
  )
}

/** 누르면 그 조건으로 목록을 거르는 수치 칸. 걸리면 남색 테두리로 보인다 */
export function StatFilterTile({
  pressed,
  onToggle,
  ...content
}: StatContentProps & { pressed: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className={statClass(content.tone, content.size)}
      aria-pressed={pressed}
      onClick={onToggle}
    >
      <StatContent label={content.label} value={content.value} sub={content.sub} />
    </button>
  )
}
