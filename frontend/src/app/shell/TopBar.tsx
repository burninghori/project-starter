import type { ReactNode } from "react"

/**
 * 상단바 — 본문 열 맨 위에 고정되는 흰 줄(app-shell-spec 3절). 오른쪽 끝에 작은 버튼만 둔다(지금은 「이름 · 역할」 프로필 메뉴 하나).
 */
export function TopBar({ actions }: { actions: ReactNode }) {
  return (
    <header className="app-topbar flex items-center justify-end gap-3.5">
      <div className="flex items-center gap-3.5">{actions}</div>
    </header>
  )
}
