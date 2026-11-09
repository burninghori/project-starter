import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Route, Routes } from "react-router"
import { afterEach, describe, expect, it, vi } from "vitest"

import { authApi, type AuthUser } from "@/api/auth"
import { ApiError } from "@/api/transport"
import { useToastStore } from "@/lib/toast-store"
import { LocationProbe, renderWithProviders } from "@/test/render"

import PasswordChangePage from "./PasswordChangePage"

const USER: AuthUser = {
  id: 1,
  loginId: "admin",
  name: "관리자",
  role: "admin",
  mustChangePassword: true,
  defaultPage: "/items",
}

function renderPage() {
  vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
  return renderWithProviders(
    <Routes>
      <Route path="/password" element={<PasswordChangePage />} />
      <Route path="*" element={<LocationProbe />} />
    </Routes>,
    { route: "/password" },
  )
}

async function fill(current: string, next: string, confirm: string) {
  const user = userEvent.setup()
  await user.type(await screen.findByLabelText("현재 비밀번호"), current)
  await user.type(screen.getByLabelText("새 비밀번호"), next)
  await user.type(screen.getByLabelText("새 비밀번호 확인"), confirm)
  await user.click(screen.getByRole("button", { name: "비밀번호 변경" }))
}

afterEach(() => {
  vi.restoreAllMocks()
  useToastStore.setState({ toasts: [] })
})

describe("PasswordChangePage", () => {
  it("규칙에 어긋나는 새 비밀번호는 서버에 보내지 않고 그 칸 아래에 알린다", async () => {
    const change = vi.spyOn(authApi, "changePassword")
    renderPage()

    await fill("old-pass-1", "short", "short")

    expect(await screen.findByRole("alert")).toHaveTextContent("비밀번호는 8자 이상이어야 합니다")
    expect(screen.getByLabelText("새 비밀번호")).toHaveAttribute("aria-invalid", "true")
    expect(change).not.toHaveBeenCalled()
  })

  it("확인이 다르면 확인 칸 아래에 알린다", async () => {
    const change = vi.spyOn(authApi, "changePassword")
    renderPage()

    await fill("old-pass-1", "new-pass-22", "new-pass-23")

    expect(await screen.findByRole("alert")).toHaveTextContent("새 비밀번호와 확인이 서로 다릅니다")
    expect(screen.getByLabelText("새 비밀번호 확인")).toHaveAttribute("aria-invalid", "true")
    expect(change).not.toHaveBeenCalled()
    expect(useToastStore.getState().toasts).toEqual([])
  })

  it("새 비밀번호의 규칙은 칸 아래 안내 한 줄로 입력 전부터 보이고, 입력하는 동안에도 남는다", async () => {
    renderPage()
    const user = userEvent.setup()
    const field = await screen.findByLabelText("새 비밀번호")
    const rule = "공백 없이 8자 이상. 영문·숫자·특수문자 조합은 필요 없습니다"

    expect(screen.getByText(rule)).toBeInTheDocument()
    expect(field).toHaveAccessibleDescription(rule)
    expect(field).not.toHaveAttribute("placeholder")

    await user.type(field, "abc")
    expect(screen.getByText(rule)).toBeInTheDocument()
  })

  it("현재 비밀번호가 틀리면 그 칸 아래에 알리고, 고쳐 입력하면 지운다", async () => {
    vi.spyOn(authApi, "changePassword").mockRejectedValue(
      new ApiError(422, "validation", "auth_current_password_invalid", undefined, { requestId: "r3" }),
    )
    renderPage()

    await fill("wrong-pass-1", "new-pass-22", "new-pass-22")

    expect(await screen.findByRole("alert")).toHaveTextContent("현재 비밀번호가 맞지 않습니다")
    const current = screen.getByLabelText("현재 비밀번호")
    expect(current).toHaveAttribute("aria-invalid", "true")

    await userEvent.setup().type(current, "x")
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
    expect(current).toHaveAttribute("aria-invalid", "false")
  })

  it("어느 칸에도 속하지 않는 오류는 버튼 위 빨간 글자 한 줄로 알린다(상자 아님)", async () => {
    vi.spyOn(authApi, "changePassword").mockRejectedValue(new TypeError("Failed to fetch"))
    renderPage()

    await fill("old-pass-1", "new-pass-22", "new-pass-22")

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("서버에 연결하지 못했습니다")
    expect(alert).toHaveClass("app-field__error")
    expect(alert).not.toHaveClass("app-note")
    // 어느 칸의 문제도 아니므로 칸은 오류로 표시하지 않는다
    expect(screen.getByLabelText("현재 비밀번호")).toHaveAttribute("aria-invalid", "false")
    expect(screen.getByLabelText("새 비밀번호")).toHaveAttribute("aria-invalid", "false")
  })

  it.each([
    [
      "관리자 초기화로 세션이 끊김(401)",
      new ApiError(401, "authentication", "auth_required", undefined, { requestId: "r5" }),
    ],
    [
      "그 사이 세션이 회수됨(409)",
      new ApiError(409, "conflict", "auth_token_version_stale", undefined, { requestId: "r6" }),
    ],
  ])("세션이 끝나면 이 화면에 머물지 않고 로그인 화면으로 간다 — %s", async (_case, error) => {
    vi.spyOn(authApi, "changePassword").mockRejectedValue(error)
    renderPage()

    await fill("old-pass-1", "new-pass-22", "new-pass-22")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/login$/)
  })

  it("칸마다 다른 이름의 보기 버튼이 있다", async () => {
    renderPage()

    expect(await screen.findByRole("button", { name: "현재 비밀번호 보기" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "새 비밀번호 보기" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "새 비밀번호 확인 보기" })).toBeInTheDocument()
  })

  it("바꾸면 성공 토스트를 남기고 기본 화면으로 간다", async () => {
    vi.spyOn(authApi, "changePassword").mockResolvedValue({ user: { ...USER, mustChangePassword: false } })
    renderPage()

    expect(await screen.findByText(/임시 비밀번호로 로그인했습니다/)).toBeInTheDocument()
    await fill("old-pass-1", "new-pass-22", "new-pass-22")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/items$/)
    expect(useToastStore.getState().toasts).toMatchObject([
      { title: "비밀번호를 바꿨습니다", tone: "success" },
    ])
    // mutationFn 은 (variables, context) 로 불린다
    expect(authApi.changePassword).toHaveBeenCalledWith(
      { currentPassword: "old-pass-1", newPassword: "new-pass-22" },
      expect.anything(),
    )
  })
})
