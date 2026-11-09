import { lazy, type ComponentType, type LazyExoticComponent } from "react"

/**
 * 화면(라우트)과 메뉴의 단일 출처. 새 화면은 여기에 한 항목을 더한다 — 라우터와 사이드바가 이 목록을 읽는다.
 *
 * - 메뉴는 처음부터 모두 보인다(결정 0003). 구분(`NavSection`)은 `NAV_SECTIONS` 순서로, 구분 안에서는 이 목록의 순서대로 그린다.
 *   항목이 없는 구분은 사이드바가 숨긴다(`SideNav`). 메뉴 항목에는 아이콘을 두지 않는다(app-shell-spec 2절).
 * - 화면이 있으면 `status: "open"` 으로 그 화면을, 아직 없으면 `status: "coming-soon"` 으로 「준비 중」 화면을 연다(사이드바에 「준비 중」
 *   표시). 기능이 완성되는 PR 이 그 항목을 `open` 으로 바꾼다.
 * - 구분 없는 메뉴(홈)는 `nav: "구분 없음"` 으로 구분 목록 위에 들여쓰기 없이 그린다.
 */
export type NavSection = "관리"

/** 메뉴에 보이는 자리 — 구분 하나, 또는 구분 없이 맨 위 */
export type NavPlace = NavSection | "구분 없음"

/** 화면이 있는 항목 */
export interface OpenPageConfig {
  status: "open"
  path: string
  label: string
  /** 사이드바 자리. null 이면 메뉴에 보이지 않는 화면(상세 화면 · 점검용 화면) */
  nav: NavPlace | null
  Component: LazyExoticComponent<ComponentType>
}

/** 화면이 아직 없는 메뉴 — 누르면 「준비 중」 화면(`ComingSoonPage`)을 연다. 메뉴라서 늘 사이드바에 보인다 */
export interface ComingSoonPageConfig {
  status: "coming-soon"
  path: string
  label: string
  nav: NavPlace
  /** 그 화면이 할 일 한 줄. 「준비 중」 화면의 설명 */
  summary: string
}

export type PageConfig = OpenPageConfig | ComingSoonPageConfig

export const NAV_SECTIONS: readonly NavSection[] = ["관리"]

export const PAGES: readonly PageConfig[] = [
  // 홈 — 서버 · 데이터베이스 · 파일 저장소 연결을 보인다(설치 점검 겸 조회 화면의 참고 구현)
  {
    status: "open",
    path: "/",
    label: "홈",
    nav: "구분 없음",
    Component: lazy(() => import("@/app/pages/home/HomePage")),
  },
  // 화면이 아직 없는 메뉴의 예 — 첫 기능을 만들 때 이 항목을 실제 메뉴로 바꾸거나 지운다
  {
    status: "coming-soon",
    path: "/settings",
    label: "설정",
    nav: "관리",
    summary: "운영에 필요한 설정을 보고 바꿉니다",
  },
]
