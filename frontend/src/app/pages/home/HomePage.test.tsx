import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { healthApi } from "@/api/health"
import { ApiError } from "@/api/transport"

import HomePage from "./HomePage"

/** 화면 테스트의 기본 형태 — 도메인 API 함수를 가로채고(vi.spyOn) 실제 훅·화면을 그린다. */
function renderWithQuery(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>)
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe("HomePage", () => {
  it("서버가 응답하면 정상으로 보인다", async () => {
    vi.spyOn(healthApi, "ready").mockResolvedValue({ status: "ok" })

    renderWithQuery(<HomePage />)

    expect(await screen.findByText("정상")).toBeInTheDocument()
  })

  it("실패하면 요청 ID 와 함께 오류를 보인다", async () => {
    vi.spyOn(healthApi, "ready").mockRejectedValue(
      new ApiError(503, "unavailable", "database_unavailable", undefined, { requestId: "abc123" }),
    )

    renderWithQuery(<HomePage />)

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("데이터베이스에 연결할 수 없습니다")
    expect(alert).toHaveTextContent("요청 ID abc123")
  })

  it("파일 저장소 실패도 어느 쪽인지 보인다", async () => {
    vi.spyOn(healthApi, "ready").mockRejectedValue(
      new ApiError(503, "unavailable", "storage_unavailable", undefined, { requestId: "def456" }),
    )

    renderWithQuery(<HomePage />)

    expect(await screen.findByRole("alert")).toHaveTextContent("파일 저장소에 연결할 수 없습니다")
  })
})
