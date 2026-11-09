import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

/**
 * 맥락 띠 — 화면 전체가 따르는 맥락(버전 · 기간 등)을 고르는 청록 띠(app-ui-spec 5절 「구조」).
 * 위 줄: 라벨 · 선택 컨트롤 · 보조 문구 · 오른쪽 버튼. 아래 줄(선택): `ContextSummaryItem` 들.
 */
export function ContextBar({
  label,
  control,
  sub,
  actions,
  summary,
}: {
  label: string
  /** 선택 컨트롤 — 보통 `ContextSelect` */
  control: ReactNode
  /** 컨트롤 옆 보조 문구. 없으면 null */
  sub: ReactNode
  actions: ReactNode
  /** 아래 요약 줄. 없으면 null */
  summary: ReactNode
}) {
  return (
    <div className="app-context mb-3 flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="app-context__label">{label}</span>
        {control}
        {sub !== null && <span className="app-context__sub">{sub}</span>}
        {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
      </div>
      {summary !== null && <div className="app-context__summary flex flex-wrap items-stretch">{summary}</div>}
    </div>
  )
}

/** 맥락 띠의 선택 컨트롤(굵은 13px, 청록 테두리) */
export function ContextSelect({
  label,
  value,
  onChange,
  children,
}: {
  /** 접근성 이름 — 띠의 라벨과 같게 */
  label: string
  value: string
  onChange: (value: string) => void
  /** `<option>` 들 */
  children: ReactNode
}) {
  return (
    <select
      className="app-context__select"
      aria-label={label}
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      {children}
    </select>
  )
}

/**
 * 요약 줄의 라벨 + 값 칸. `emphasis="large"` 는 최종 결과처럼 가장 중요한 값(19px)이다.
 * 값이 상태라면 `value` 에 `StatusText` 를 넘겨 상태색을 입힌다.
 */
export function ContextSummaryItem({
  label,
  value,
  emphasis,
  children,
}: {
  label: string
  value: ReactNode
  emphasis: "normal" | "large"
  /** 값 아래 설명. 없으면 null */
  children: ReactNode
}) {
  return (
    <div className="app-context__item flex flex-col gap-px">
      <span className="app-context__item-label">{label}</span>
      <span className={cn("app-context__item-value", emphasis === "large" && "app-context__item-value--lg")}>
        {value}
      </span>
      {children !== null && <span>{children}</span>}
    </div>
  )
}

/**
 * 요약 줄의 글 칸 — 라벨 없이 근거·안내 문장만 있고 남는 폭을 채운다(최소 220px).
 * 문장 안의 `<b>` 는 14px 로 커진다. 둘째 줄의 작은 설명은 `app-note-inline` 으로 감싼다.
 */
export function ContextSummaryText({ children }: { children: ReactNode }) {
  return <div className="app-context__item app-context__text min-w-[220px] flex-1">{children}</div>
}
