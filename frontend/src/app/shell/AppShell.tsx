import { Outlet, useNavigate } from "react-router"

import { useCurrentUser, useLogout } from "@/api/auth"
import { APP_MARK, APP_NAME, APP_SUBTITLE } from "@/app/brand"
import { NAV_SECTIONS, PAGES } from "@/app/routing/pages-config"
import { OverlayHost } from "@/components/overlay/OverlayHost"
import { Toaster } from "@/components/overlay/Toaster"
import { MenuButton } from "@/components/ui/MenuButton"

import { SideNav } from "./SideNav"
import { TopBar } from "./TopBar"

/**
 * 앱 셸 — 사이드바(브랜드 + 메뉴) + 본문 열(상단 바 + 여백 있는 본문). 메뉴는 pages-config 가 정한다(`SideNav`).
 * 브랜드는 마크 + 서비스명 + 부제(`app/brand.ts`), 사이드바 하단 정보 없음, 상단 바는 오른쪽 프로필 메뉴만(app-shell-spec 2·3절).
 * 치수·모양은 app-shell-spec.
 */
export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="app-brand">
          {/* 마크는 장식이라 화면 낭독기에서 숨긴다(서비스명만 읽는다) */}
          <span className="app-brand__mark" aria-hidden="true">
            {APP_MARK}
          </span>
          <div>
            <span className="app-brand__name">{APP_NAME}</span>
            <span className="app-brand__sub">{APP_SUBTITLE}</span>
          </div>
        </div>
        <SideNav sections={NAV_SECTIONS} pages={PAGES} />
      </aside>
      <div className="app-main">
        <TopBar actions={<ProfileMenu />} />
        <main className="app-main__body">
          <Outlet />
        </main>
      </div>
      <OverlayHost />
      <Toaster />
    </div>
  )
}

/** 상단 바 오른쪽 「이름 · 역할」 버튼 → 프로필 메뉴 → 「로그아웃」. 역할은 화면 이름 목록이 정해질 때까지 코드값 그대로 */
function ProfileMenu() {
  const user = useCurrentUser()
  const logout = useLogout()
  const navigate = useNavigate()
  return (
    <MenuButton
      label={`${user.name} · ${user.role}`}
      variant="secondary"
      size="sm"
      align="end"
      items={[
        {
          label: "로그아웃",
          onSelect: () =>
            logout.mutate(undefined, {
              // 훅의 onSettled(세션 정리)가 끝난 뒤 불린다. 가드의 자동 이동에 맡기면 returnTo 가 남아 다음 로그인이 defaultPage 대신
              // 이전 화면으로 간다. flushSync: 세션 정리 알림(setTimeout 0)이 라우터 이동(transition)보다 먼저 가드에 닿으면 returnTo 를
              // 담은 이동이 한 번 더 생기므로, 이동을 동기 커밋해 가드가 그 상태를 보기 전에 셸을 떼어 낸다(app-shell-spec 5절)
              onSettled: () => navigate("/login", { replace: true, flushSync: true }),
            }),
        },
      ]}
    />
  )
}
