import type { ReactNode } from "react"

import { cn } from "@/lib/cn"

/**
 * 화면·모달 안의 안내 상자. 기본은 무채색이고, `warn`(호박)은 「주의해야 하는 것」에만 쓴다(design-concept 3절).
 * 조회 실패는 `QueryErrorPanel` 이 맡는다.
 */
export function Note({ tone, children }: { tone: "plain" | "warn"; children: ReactNode }) {
  return <div className={cn("app-note", tone === "warn" && "app-note--warn")}>{children}</div>
}
