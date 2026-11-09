import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

interface ResultBandProps {
  /** ok: 긍정(청록) · danger: 부정(적) · pending: 아직 산출 전(무채) */
  tone: "ok" | "danger" | "pending"
  /** 무엇의 결과인지 — 예: 「검사 결과」 */
  label: string
  value: string
  /** 결과의 근거·조건 한 줄 */
  condition: ReactNode
  /** 오른쪽 버튼. 없으면 null */
  actions: ReactNode
}

/** 결과 하나를 크게 알리는 가로 띠(app-ui-spec 5절 「결과 띠」) */
export function ResultBand({ tone, label, value, condition, actions }: ResultBandProps) {
  return (
    <div
      className={cn(
        "app-result flex flex-wrap items-center gap-2.5",
        tone === "ok" && "app-result--ok",
        tone === "danger" && "app-result--danger",
      )}
    >
      <span className="app-result__label">{label}</span>
      <span className="app-result__value">{value}</span>
      <span className="app-result__cond">{condition}</span>
      {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  )
}
