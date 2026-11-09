import { render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router"
import { describe, expect, it } from "vitest"

import { SideNav, type SideNavPage } from "./SideNav"

/** 실제 PAGES 에 묶지 않는다 — 어떤 메뉴가 열려 있는지는 기능 Issue 마다 바뀐다(실제 메뉴는 router.test 가 본다) */
const SECTIONS = ["업무", "관리"] as const

function renderNav(route: string, pages: readonly SideNavPage[]) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <SideNav sections={SECTIONS} pages={pages} />
    </MemoryRouter>,
  )
}

describe("SideNav", () => {
  it("항목이 없는 구분은 보이지 않고, 메뉴에 없는 화면(nav: null)은 그리지 않는다", () => {
    renderNav("/items", [
      { status: "open", path: "/items", label: "항목", nav: "업무" },
      { status: "open", path: "/items/:id", label: "항목 상세", nav: null },
    ])

    expect(screen.getByText("업무")).toBeInTheDocument()
    expect(screen.queryByText("관리")).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: "항목" })).toHaveAttribute("href", "/items")
    expect(screen.queryByRole("link", { name: "항목 상세" })).not.toBeInTheDocument()
  })

  it("상세 경로에서도 상위 메뉴가 강조되고, 홈은 그 경로에서만 강조된다", () => {
    renderNav("/items/7", [
      { status: "open", path: "/", label: "홈", nav: "구분 없음" },
      { status: "open", path: "/items", label: "항목", nav: "업무" },
    ])

    expect(screen.getByRole("link", { name: "항목" })).toHaveAttribute("aria-current", "page")
    expect(screen.getByRole("link", { name: "홈" })).not.toHaveAttribute("aria-current")
  })

  it("「구분 없음」 메뉴는 구분 머리 없이 맨 위에 그린다 — 목록에서 뒤에 있어도 먼저", () => {
    renderNav("/items", [
      { status: "open", path: "/items", label: "항목", nav: "업무" },
      { status: "open", path: "/", label: "홈", nav: "구분 없음" },
    ])

    const nav = screen.getByRole("navigation", { name: "주 메뉴" })
    const links = within(nav).getAllByRole("link")
    expect(links.map((link) => link.getAttribute("href"))).toEqual(["/", "/items"])
    // 첫 구분 머리보다 앞이다 — 「구분 없음」이라는 머리는 그리지 않는다
    expect(nav.textContent?.startsWith("홈")).toBe(true)
    expect(screen.queryByText("구분 없음")).not.toBeInTheDocument()
  })

  it("화면이 없는 메뉴는 이름 옆에 「준비 중」을 달고 누를 수 있다", () => {
    renderNav("/settings", [
      { status: "open", path: "/items", label: "항목", nav: "업무" },
      { status: "coming-soon", path: "/settings", label: "설정", nav: "관리" },
    ])

    // 표시 글자는 링크 이름에 들어간다
    const settings = screen.getByRole("link", { name: "설정 준비 중" })
    expect(settings).toHaveAttribute("href", "/settings")
    expect(settings).toHaveAttribute("aria-current", "page")
    // 화면이 있는 메뉴에는 표시가 없다
    expect(screen.getByRole("link", { name: "항목" })).toHaveTextContent(/^항목$/)
  })
})
