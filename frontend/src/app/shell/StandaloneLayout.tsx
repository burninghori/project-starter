import type { ReactNode } from "react"

import { APP_NAME } from "@/app/brand"

/**
 * 셸(사이드바·상단 바) 밖 화면의 틀 — 로그인·비밀번호 변경(app-shell-spec 5절).
 * 바탕 가운데 한 줄에 브랜드(서비스명, 로그인 화면이면 그 아래 설명 한 줄)를 두고 그 아래 카드를 놓는다.
 * `description` 은 로그인 화면만 `LOGIN_DESCRIPTION` 을 넘기고 나머지는 null(서비스명만)이다.
 * 화면은 카드 안에 제목(`app-standalone__title`)과 폼을 넣는다.
 */
export function StandaloneLayout({
  description,
  children,
}: {
  description: string | null
  children: ReactNode
}) {
  return (
    <div className="app-standalone">
      <main className="app-standalone__main flex flex-col gap-5">
        <div className="flex flex-col items-center gap-1 text-center">
          <p className="app-title">{APP_NAME}</p>
          {description !== null && <p className="app-desc break-keep">{description}</p>}
        </div>
        <div className="app-standalone__card flex flex-col gap-4">{children}</div>
      </main>
    </div>
  )
}
