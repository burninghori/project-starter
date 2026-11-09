import { NavLink } from "react-router"

import type { ComingSoonPageConfig, OpenPageConfig } from "@/app/routing/pages-config"
import { Tag } from "@/components/ui/Tag"
import { cn } from "@/lib/cn"

/** 사이드바가 읽는 칸만. 구분 이름은 문자열로 받는다 — 구분 목록은 pages-config 가 정하고, 테스트는 제 구분으로 그린다 */
export type SideNavPage =
  | (Pick<OpenPageConfig, "status" | "path" | "label"> & { nav: string | null })
  | (Pick<ComingSoonPageConfig, "status" | "path" | "label"> & { nav: string })

/**
 * 사이드바 메뉴 — 구분 없는 메뉴(「구분 없음」)를 맨 위에 들여쓰기 없이 두고, 그 아래 구분 순서대로 그린다. 항목이 없는 구분은 그리지 않는다
 * (app-shell-spec 2절). 메뉴 항목에는 아이콘을 두지 않는다.
 * `NavLink` 에 `end` 를 두지 않아 상세 경로(`/items/7`)에서도 상위 메뉴가 강조된다(app-shell-spec 5절).
 * 홈 `/` 만 `end` 를 둔다 — 없으면 모든 경로에서 홈이 강조된다.
 */
export function SideNav({ sections, pages }: { sections: readonly string[]; pages: readonly SideNavPage[] }) {
  return (
    <nav className="app-nav" aria-label="주 메뉴">
      {pages
        .filter((page) => page.nav === "구분 없음")
        .map((page) => (
          <NavItem key={page.path} page={page} top />
        ))}
      {sections.map((section) => {
        const items = pages.filter((page) => page.nav === section)
        if (items.length === 0) return null
        return (
          <div key={section}>
            <div className="app-nav__heading">{section}</div>
            {items.map((page) => (
              <NavItem key={page.path} page={page} top={false} />
            ))}
          </div>
        )
      })}
    </nav>
  )
}

/**
 * 메뉴 항목 하나. 화면이 없는 메뉴는 이름 오른쪽 끝에 「준비 중」 표시를 단다 — 흐리게 하지 않고 누르면 「준비 중」 화면이 열린다(결정 0003).
 * 표시 글자는 링크 이름에 들어간다(화면 낭독기는 「설정 준비 중」으로 읽는다).
 */
function NavItem({ page, top }: { page: SideNavPage; top: boolean }) {
  return (
    <NavLink
      to={page.path}
      end={page.path === "/"}
      className={({ isActive }) =>
        cn("app-nav__item", top && "app-nav__item--top", isActive && "app-nav__item--active")
      }
    >
      {page.label}
      {page.status === "coming-soon" && (
        <>
          {" "}
          <Tag tone="neutral">준비 중</Tag>
        </>
      )}
    </NavLink>
  )
}
