import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Route, Routes } from "react-router"
import { afterEach, describe, expect, it, vi } from "vitest"

import { authApi, type AuthUser } from "@/api/auth"
import { ApiError } from "@/api/transport"
import { LocationProbe, renderWithProviders } from "@/test/render"

import LoginPage from "./LoginPage"

const USER: AuthUser = {
  id: 1,
  loginId: "admin",
  name: "관리자",
  role: "admin",
  mustChangePassword: false,
  defaultPage: "/items",
}

function notLoggedIn() {
  return new ApiError(401, "authentication", "auth_required", undefined, { requestId: "r1" })
}

function renderLogin(route: string | { pathname: string; state: unknown } = "/login") {
  return renderWithProviders(
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<LocationProbe />} />
    </Routes>,
    { route },
  )
}

async function submit(loginId: string, password: string) {
  const user = userEvent.setup()
  await user.type(await screen.findByRole("textbox", { name: "아이디" }), loginId)
  await user.type(screen.getByLabelText("비밀번호"), password)
  await user.click(screen.getByRole("button", { name: "로그인" }))
}

/** 브라우저 자동 채우기처럼 — 입력 이벤트 없이 칸에 값만 넣는다 */
function fillWithoutEvents(element: HTMLElement, value: string) {
  if (!(element instanceof HTMLInputElement)) throw new Error("입력 칸이 아니다")
  element.value = value
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("LoginPage", () => {
  it("로그인하면 서버가 준 기본 화면으로 간다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: USER })

    renderLogin()
    await submit("admin", "secret-pw-1")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
    // mutationFn 은 (variables, context) 로 불린다
    expect(authApi.login).toHaveBeenCalledWith(
      { loginId: "admin", password: "secret-pw-1" },
      expect.anything(),
    )
  })

  it("기본 화면이 등록되지 않은 경로라도 다른 곳으로 대체하지 않는다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: { ...USER, defaultPage: "/nowhere" } })

    renderLogin()
    await submit("admin", "secret-pw-1")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/nowhere$/)
  })

  it("돌아올 경로가 있으면 그곳으로 간다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: USER })

    renderLogin({ pathname: "/login", state: { returnTo: "/items?page=2" } })
    await submit("admin", "secret-pw-1")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
  })

  it("비밀번호를 바꿔야 하는 계정은 비밀번호 변경 화면으로 간다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: { ...USER, mustChangePassword: true } })

    renderLogin()
    await submit("admin", "temp-pw-123")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/password$/)
  })

  it("아이디나 비밀번호가 틀리면 한 문구로 알리고, 아이디는 남긴 채 비밀번호만 비워 다시 입력하게 한다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockRejectedValue(
      new ApiError(401, "authentication", "auth_invalid_credentials", undefined, { requestId: "r2" }),
    )

    renderLogin()
    await submit("admin", "wrong-pw-1")

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("아이디 또는 비밀번호가 맞지 않습니다")
    // 상자가 아니라 칸 오류와 같은 빨간 글자 한 줄(FormError)이다
    expect(alert).toHaveClass("app-field__error")
    expect(alert).not.toHaveClass("app-note")
    expect(screen.queryByTestId("location")).not.toBeInTheDocument()
    expect(screen.getByRole("textbox", { name: "아이디" })).toHaveValue("admin")
    const password = screen.getByLabelText("비밀번호")
    expect(password).toHaveValue("")
    expect(password).toHaveFocus()
  })

  it("브라우저가 입력 이벤트 없이 채운 아이디 · 비밀번호도 「로그인」 한 번에 보낸다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: USER })

    renderLogin()
    fillWithoutEvents(await screen.findByRole("textbox", { name: "아이디" }), "admin")
    fillWithoutEvents(screen.getByLabelText("비밀번호"), "secret-pw-1")
    // 빈 칸으로 버튼을 끄지 않는다 — 꺼져 있으면 첫 클릭이 버튼에 닿지 않아 두 번 눌러야 한다
    expect(screen.getByRole("button", { name: "로그인" })).toBeEnabled()
    await userEvent.setup().click(screen.getByRole("button", { name: "로그인" }))

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
    expect(authApi.login).toHaveBeenCalledTimes(1)
    expect(authApi.login).toHaveBeenCalledWith(
      { loginId: "admin", password: "secret-pw-1" },
      expect.anything(),
    )
  })

  it("빈 칸이면 요청하지 않고 그 칸 아래에 알리며 첫 빈 칸에 커서를 둔다 — 고치기 시작하면 그 칸의 문구를 지운다", async () => {
    const user = userEvent.setup()
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockResolvedValue({ user: USER })

    renderLogin()
    const loginId = await screen.findByRole("textbox", { name: "아이디" })
    await user.click(screen.getByRole("button", { name: "로그인" }))

    expect(authApi.login).not.toHaveBeenCalled()
    expect(screen.getAllByRole("alert").map((alert) => alert.textContent)).toEqual([
      "아이디를 입력하세요",
      "비밀번호를 입력하세요",
    ])
    expect(loginId).toHaveFocus()
    expect(loginId).toHaveAttribute("aria-invalid", "true")

    await user.type(loginId, "admin")
    expect(screen.queryByText("아이디를 입력하세요")).not.toBeInTheDocument()
    expect(screen.getByText("비밀번호를 입력하세요")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "로그인" }))
    expect(screen.getByLabelText("비밀번호")).toHaveFocus()
    expect(authApi.login).not.toHaveBeenCalled()

    await user.type(screen.getByLabelText("비밀번호"), "secret-pw-1")
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "로그인" }))
    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
  })

  it("로그인 실패 뒤 빈 칸으로 다시 누르면 지난 실패 문구를 내리고 빈 칸만 알린다", async () => {
    const user = userEvent.setup()
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockRejectedValue(
      new ApiError(401, "authentication", "auth_invalid_credentials", undefined, { requestId: "r3" }),
    )

    renderLogin()
    await submit("admin", "wrong-pw-1")
    expect(await screen.findByText("아이디 또는 비밀번호가 맞지 않습니다")).toBeInTheDocument()

    // 실패하면 비밀번호가 비워진다 — 그대로 다시 누른다
    await user.click(screen.getByRole("button", { name: "로그인" }))

    expect(screen.queryByText("아이디 또는 비밀번호가 맞지 않습니다")).not.toBeInTheDocument()
    expect(screen.getAllByRole("alert").map((alert) => alert.textContent)).toEqual(["비밀번호를 입력하세요"])
    expect(authApi.login).toHaveBeenCalledTimes(1)
  })

  it("요청을 처리하는 동안에만 「로그인」을 끈다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())
    vi.spyOn(authApi, "login").mockReturnValue(new Promise(() => {}))

    renderLogin()
    await submit("admin", "secret-pw-1")

    const button = screen.getByRole("button", { name: "로그인" })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute("aria-busy", "true")
  })

  it("보이는 제목 없이 폼과 도움말만 둔다 — 제목은 화면 낭독기에만 있다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(notLoggedIn())

    renderLogin()

    expect(await screen.findByRole("heading", { level: 1, name: "로그인" })).toHaveClass("sr-only")
    expect(screen.getByText("비밀번호를 잊었다면 관리자에게 문의하세요")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "비밀번호 보기" })).toBeInTheDocument()
  })

  it("이미 로그인돼 있으면 폼 없이 바로 이동한다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })

    renderLogin()

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
    expect(screen.queryByRole("button", { name: "로그인" })).not.toBeInTheDocument()
  })
})
