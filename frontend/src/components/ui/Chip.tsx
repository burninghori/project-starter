import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

interface ChipProps {
  label: string
  count: number
  /** 걸리지 않았을 때 건수의 색 — 그 칩이 거르는 상태의 색(예: Pass 청록 · Fail 적). 상태가 아니면 plain */
  countTone: "plain" | "ok" | "warn" | "danger"
  pressed: boolean
  /** 0건처럼 고를 수 없을 때. 흐리게 보이고 누를 수 없다 — 숨기지 않는다(design-concept 4절) */
  disabled: boolean
  /** `main` 은 합이 전체가 되는 주 축, `subset` 은 합계에 들지 않는 부분집합 축(점선) */
  axis: "main" | "subset"
  onToggle: () => void
}

/**
 * 목록을 한 조건으로 거르는 칩. 걸리면 남색으로 채운다(`subset` 은 적색).
 * 한 줄의 칩은 단일 선택이다 — 어떤 칩을 걸 때 다른 칩을 푸는 것은 화면 상태가 맡는다.
 */
export function Chip({ label, count, countTone, pressed, disabled, axis, onToggle }: ChipProps) {
  return (
    <button
      type="button"
      className={cn("app-chip", axis === "subset" && "app-chip--subset")}
      aria-pressed={pressed}
      disabled={disabled}
      title={disabled ? "해당 건이 없습니다" : undefined}
      onClick={onToggle}
    >
      {/* 공백 — 화면은 gap 이 띄우지만 접근성 이름이 「실패1,482」로 붙지 않게 한다 */}
      {label}{" "}
      <span
        className={cn("app-chip__count app-num", countTone !== "plain" && `app-chip__count--${countTone}`)}
      >
        {count.toLocaleString()}
      </span>
    </button>
  )
}

/** 칩 한 줄. 오른쪽 끝(`end`)에 실행 버튼 등을 둔다 — 없으면 null */
export function ChipBar({ children, end }: { children: ReactNode; end: ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-[7px]">
      {children}
      {end !== null && <div className="ml-auto flex items-center gap-[7px]">{end}</div>}
    </div>
  )
}

/** 축이 다른 칩 사이의 세로 구분선 */
export function ChipSeparator() {
  return <span className="app-chip-sep" aria-hidden />
}
