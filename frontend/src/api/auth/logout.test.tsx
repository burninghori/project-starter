import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/api/transport"

import { authApi, authKeys, useLogout, type AuthUser } from "./index"

/**
 * 로그아웃 동작 — 버튼은 앱 셸(상단 바 프로필 메뉴)이 붙이고, 여기서는 그 버튼이 부를 동작만 확인한다.
 */

const USER: AuthUser = {
  id: 1,
  loginId: "admin",
  name: "관리자",
  role: "admin",
  mustChangePassword: false,
  defaultPage: "/items",
}

// 로그아웃한 뒤 다음 사용자에게 보이면 안 되는 이전 사용자의 화면 데이터
const PREVIOUS_USER_DATA_KEY = ["items", "list"] as const

function renderLogout() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  client.setQueryData(authKeys.me(), USER)
  client.setQueryData(PREVIOUS_USER_DATA_KEY, ["이전 사용자의 항목 목록"])
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  const { result } = renderHook(() => useLogout(), { wrapper })
  return { client, result }
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("useLogout", () => {
  it("로그아웃 API 를 부르고, 로그인 상태를 「없음」으로 바꾸며 이전 사용자의 화면 데이터를 지운다", async () => {
    vi.spyOn(authApi, "logout").mockResolvedValue(undefined)
    const { client, result } = renderLogout()

    act(() => result.current.mutate())

    await waitFor(() => expect(client.getQueryData(authKeys.me())).toBeNull())
    expect(client.getQueryData(PREVIOUS_USER_DATA_KEY)).toBeUndefined()
    expect(authApi.logout).toHaveBeenCalledTimes(1)
  })

  it("서버가 실패해도(이미 세션이 끝난 401 등) 이 브라우저의 로그인 상태는 지운다", async () => {
    vi.spyOn(authApi, "logout").mockRejectedValue(
      new ApiError(401, "authentication", "auth_required", undefined, { requestId: "r1" }),
    )
    const { client, result } = renderLogout()

    act(() => result.current.mutate())

    await waitFor(() => expect(client.getQueryData(authKeys.me())).toBeNull())
    expect(client.getQueryData(PREVIOUS_USER_DATA_KEY)).toBeUndefined()
  })
})
