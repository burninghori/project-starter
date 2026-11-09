import { screen } from "@testing-library/react"
import { Route, Routes } from "react-router"
import { afterEach, describe, expect, it, vi } from "vitest"

import { authApi, type AuthUser } from "@/api/auth"
import { ApiError, fetchJson } from "@/api/transport"
import { LocationProbe, renderWithProviders } from "@/test/render"

import { RequireLogin, RequirePasswordChanged } from "./guards"

const USER: AuthUser = {
  id: 1,
  loginId: "admin",
  name: "관리자",
  role: "admin",
  mustChangePassword: false,
  defaultPage: "/items",
}

// 세션이 끝난 뒤 다음 사용자에게 보이면 안 되는 이전 사용자의 화면 데이터
const PREVIOUS_USER_DATA_KEY = ["items", "list"] as const

function unauthorizedResponse(): Response {
  return new Response(
    JSON.stringify({
      error: {
        contract: "semantic-v1",
        family: "authentication",
        code: "auth_required",
        diagnostic: { requestId: "r" },
      },
    }),
    { status: 401, headers: { "content-type": "application/json" } },
  )
}

function renderGuards(route: string) {
  return renderWithProviders(
    <Routes>
      <Route element={<RequireLogin />}>
        <Route path="/password" element={<p>비밀번호 변경 화면</p>} />
        <Route element={<RequirePasswordChanged />}>
          <Route path="/items" element={<p>항목 목록 본문</p>} />
        </Route>
      </Route>
      <Route path="/login" element={<LocationProbe />} />
    </Routes>,
    { route },
  )
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe("RequireLogin", () => {
  it("로그인돼 있지 않으면 로그인 화면으로 보내고 돌아올 경로를 남긴다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(
      new ApiError(401, "authentication", "auth_required", undefined, { requestId: "r1" }),
    )

    renderGuards("/items?page=2")

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/login$/)
    expect(screen.getByTestId("location-state")).toHaveTextContent('{"returnTo":"/items?page=2"}')
  })

  it("로그인돼 있으면 본문을 그린다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })

    renderGuards("/items")

    expect(await screen.findByText("항목 목록 본문")).toBeInTheDocument()
  })

  it("서버 상태를 알 수 없으면 오류를 보인다", async () => {
    vi.spyOn(authApi, "me").mockRejectedValue(new TypeError("Failed to fetch"))

    renderGuards("/items")

    expect(await screen.findByRole("alert")).toHaveTextContent("로그인 상태를 확인하지 못했습니다")
  })

  it("세션이 중간에 끝나면(다른 요청의 401) 이전 화면 데이터를 지우고 로그인 화면으로 간다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: USER })
    const { client } = renderGuards("/items")
    expect(await screen.findByText("항목 목록 본문")).toBeInTheDocument()
    client.setQueryData(PREVIOUS_USER_DATA_KEY, ["이전 사용자의 항목 목록"])

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(unauthorizedResponse()))
    await expect(fetchJson("/items")).rejects.toMatchObject({ status: 401 })

    expect(await screen.findByTestId("location")).toHaveTextContent(/^\/login$/)
    // 다른 계정으로 다시 로그인했을 때 이전 사용자의 응답이 보이지 않게 지워져 있다
    expect(client.getQueryData(PREVIOUS_USER_DATA_KEY)).toBeUndefined()
  })
})

describe("RequirePasswordChanged", () => {
  it("비밀번호를 바꿔야 하면 변경 화면으로 보낸다", async () => {
    vi.spyOn(authApi, "me").mockResolvedValue({ user: { ...USER, mustChangePassword: true } })

    renderGuards("/items")

    expect(await screen.findByText("비밀번호 변경 화면")).toBeInTheDocument()
  })
})
