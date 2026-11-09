import { screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { authApi, type AuthUser } from "@/api/auth"
import { healthApi } from "@/api/health"
import { ApiError } from "@/api/transport"
import { APP_MARK, APP_NAME, APP_SUBTITLE } from "@/app/brand"
import { renderApp } from "@/test/render"

/** 실제 라우트 트리로 보는 진입·홈·메뉴·「준비 중」 화면·없는 주소·셸·로그아웃 */

const USER: AuthUser = {
  id: 1,
  loginId: "admin",
  name: "관리자",
  role: "admin",
  mustChangePassword: false,
  defaultPage: "/",
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("라우트 트리", () => {
  it("홈(/)은 서버 연결 상태를 보인다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
    vi.spyOn(healthApi, "ready").mockResolvedValue({ status: "ok" })

    renderApp({ route: "/" })

    expect(await screen.findByRole("heading", { level: 1, name: "홈" })).toBeInTheDocument()
    expect(await screen.findByText("정상")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "홈" })).toHaveAttribute("aria-current", "page")
  })

  it("좌측 메뉴는 pages-config 순서로 보이고, 화면이 없는 메뉴에 「준비 중」을 단다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
    vi.spyOn(healthApi, "ready").mockResolvedValue({ status: "ok" })

    renderApp({ route: "/" })

    await screen.findByRole("heading", { level: 1, name: "홈" })
    const menu = screen.getByRole("navigation", { name: "주 메뉴" })
    const links = within(menu).getAllByRole("link")
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["홈", "/"],
      ["설정 준비 중", "/settings"],
    ])
    expect(menu).toHaveTextContent(/^홈관리설정/)
  })

  it("화면이 없는 메뉴를 누르면 셸 안에서 「준비 중」 화면이 열린다", async () => {
    const user = userEvent.setup()
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
    vi.spyOn(healthApi, "ready").mockResolvedValue({ status: "ok" })
    const { router } = renderApp({ route: "/" })
    await screen.findByRole("heading", { level: 1, name: "홈" })

    await user.click(screen.getByRole("link", { name: "설정 준비 중" }))

    expect(await screen.findByRole("heading", { level: 1, name: "설정" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/settings")
    expect(screen.getByText("준비 중인 화면입니다")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "설정 준비 중" })).toHaveAttribute("aria-current", "page")
    expect(screen.getByRole("link", { name: "홈" })).not.toHaveAttribute("aria-current")
  })

  it("없는 주소는 셸 안에서 「페이지를 찾을 수 없습니다」를 보인다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })

    renderApp({ route: "/no-such" })

    expect(await screen.findByText("페이지를 찾을 수 없습니다")).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "주 메뉴" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "첫 화면으로" })).toHaveAttribute("href", "/")
  })
})

describe("앱 셸", () => {
  it("마크·서비스명·부제를 보이고 상단 바에는 「이름 · 역할」 메뉴 버튼만 있다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })

    renderApp({ route: "/settings" })

    await screen.findByRole("heading", { level: 1, name: "설정" })
    // 마크는 장식 — 화면 낭독기는 서비스명만 읽는다
    expect(screen.getByText(APP_MARK)).toHaveAttribute("aria-hidden", "true")
    expect(screen.getByText(APP_NAME)).toBeInTheDocument()
    expect(screen.getByText(APP_SUBTITLE)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "관리자 · admin" })).toHaveAttribute("aria-haspopup", "menu")
  })

  it("로그아웃하면 로그인 화면으로 가고, 다시 로그인하면 돌아올 경로 없이 기본 화면으로 간다", async () => {
    const user = userEvent.setup()
    const loggedIn = { ...USER, defaultPage: "/" }
    vi.spyOn(authApi, "me").mockResolvedValue({ user: loggedIn })
    vi.spyOn(authApi, "logout").mockResolvedValue(undefined)
    vi.spyOn(authApi, "login").mockResolvedValue({ user: loggedIn })
    vi.spyOn(healthApi, "ready").mockResolvedValue({ status: "ok" })
    const { router } = renderApp({ route: "/settings" })
    await screen.findByRole("heading", { level: 1, name: "설정" })

    await user.click(screen.getByRole("button", { name: "관리자 · admin" }))
    await user.click(screen.getByRole("menuitem", { name: "로그아웃" }))

    expect(await screen.findByRole("button", { name: "로그인" })).toBeInTheDocument()
    expect(authApi.logout).toHaveBeenCalledTimes(1)
    expect(router.state.location.pathname).toBe("/login")
    // 가드가 남기는 returnTo 가 없어야 다음 로그인이 defaultPage 로 간다
    expect(router.state.location.state).toBeNull()

    await user.type(screen.getByRole("textbox", { name: "아이디" }), "admin")
    await user.type(screen.getByLabelText("비밀번호"), "secret-pw-1")
    await user.click(screen.getByRole("button", { name: "로그인" }))

    expect(await screen.findByRole("heading", { level: 1, name: "홈" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/")
  })

  it("로그아웃 요청이 실패해도(이미 끝난 세션) 로그인 화면으로 간다", async () => {
    const user = userEvent.setup()
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
    vi.spyOn(authApi, "logout").mockRejectedValue(
      new ApiError(401, "authentication", "auth_required", undefined, { requestId: "r1" }),
    )
    const { router } = renderApp({ route: "/settings" })
    await screen.findByRole("heading", { level: 1, name: "설정" })

    await user.click(screen.getByRole("button", { name: "관리자 · admin" }))
    await user.click(screen.getByRole("menuitem", { name: "로그아웃" }))

    expect(await screen.findByRole("button", { name: "로그인" })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe("/login")
    expect(router.state.location.state).toBeNull()
  })
})
