import { ArrowLeft, ArrowRight } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

import { Button } from "./Button"

/**
 * 화면의 뼈대 조각 — 페이지 머리 · 섹션 머리 · 카드 · 상세 면 · 상세 상단 줄.
 * 치수는 app-shell-spec 4절, 모양은 app-ui-spec 5절 「구조」.
 */

/** 페이지 제목(21px) + 설명 한 줄. 화면마다 맨 위에 하나 */
export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <header className="mb-[18px] flex flex-col gap-1">
      <h1 className="app-title">{title}</h1>
      <p className="app-desc">{description}</p>
    </header>
  )
}

/** 섹션 제목 + 주석 + 오른쪽 동작 버튼 */
export function SectionHeader({
  title,
  note,
  actions,
}: {
  title: string
  note: ReactNode
  actions: ReactNode
}) {
  return (
    <div className="mb-2 flex flex-wrap items-center gap-2.5">
      <h2 className="app-section-title">{title}</h2>
      {note !== null && <span className="app-note-inline">{note}</span>}
      {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  )
}

interface CardProps {
  /** 머리줄 제목. 머리줄 없는 카드(표만 감싸기)면 null */
  title: string | null
  /** 머리줄의 주석 · 오른쪽 버튼. 없으면 null */
  note: ReactNode
  actions: ReactNode
  children: ReactNode
}

/**
 * 블록 하나. 표를 넣으면 테두리 없이 카드 가장자리에 붙고, 여백이 필요한 내용은 `CardBody` 로 감싼다.
 */
export function Card({ title, note, actions, children }: CardProps) {
  return (
    <section className="app-card">
      {title !== null && (
        <div className="app-card__head flex items-center gap-2.5">
          <h3 className="app-card__title">{title}</h3>
          {note !== null && <span className="app-note-inline">{note}</span>}
          {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  )
}

export function CardBody({ children }: { children: ReactNode }) {
  return <div className="app-card__body">{children}</div>
}

/**
 * 상세 면 — 위에서 고른 대상의 내용을 아래에 보일 때. 머리줄 제목은 회색이다.
 * `selected` 면 청록 테두리 + 머리줄 연청록으로 「지금 고른 대상」임을 보인다.
 */
export function Panel({
  title,
  meta,
  selected,
  extra,
  children,
}: {
  title: ReactNode
  /** 제목 바로 옆의 짧은 정보(실행 일시 등). 없으면 null */
  meta: ReactNode
  selected: boolean
  /** 머리줄 오른쪽 끝(조건 설명 · 링크 등). 없으면 null */
  extra: ReactNode
  children: ReactNode
}) {
  return (
    <section className={cn("app-panel", selected && "app-panel--selected")}>
      <div className="app-panel__head flex flex-wrap items-center gap-2.5">
        <h3 className="app-panel__title">{title}</h3>
        {meta}
        {extra !== null && <div className="ml-auto flex items-center gap-2">{extra}</div>}
      </div>
      <div className="app-panel__body">{children}</div>
    </section>
  )
}

/**
 * 상세 화면 맨 위 줄 — 「← 목록으로」 · 경로 · 「← 이전」 「다음 →」.
 * 이전·다음은 목록에 걸린 필터와 순서를 따른다. 끝이라 갈 곳이 없으면 null 로 넘겨 비활성으로 둔다.
 */
export function BackBar({
  crumb,
  onBack,
  onPrev,
  onNext,
}: {
  crumb: string
  onBack: () => void
  onPrev: (() => void) | null
  onNext: (() => void) | null
}) {
  return (
    <div className="mb-2.5 flex items-center gap-2.5">
      <Button variant="secondary" size="sm" onClick={onBack}>
        <ArrowLeft size={14} aria-hidden />
        목록으로
      </Button>
      <span className="app-crumb">{crumb}</span>
      <span className="flex-1" />
      <Button variant="secondary" size="sm" disabled={onPrev === null} onClick={onPrev ?? undefined}>
        <ArrowLeft size={14} aria-hidden />
        이전
      </Button>
      <Button variant="secondary" size="sm" disabled={onNext === null} onClick={onNext ?? undefined}>
        다음
        <ArrowRight size={14} aria-hidden />
      </Button>
    </div>
  )
}
