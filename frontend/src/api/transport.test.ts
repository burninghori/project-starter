import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError, apiPath, fetchJson, setUnauthorizedHandler } from "./transport"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } })
}

function unauthorizedBody() {
  return {
    error: {
      contract: "semantic-v1",
      family: "authentication",
      code: "auth_required",
      diagnostic: { requestId: "r401" },
    },
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
  setUnauthorizedHandler(null)
})

describe("apiPath", () => {
  it("업무 경로에 /api/v1 을 붙이고 query 를 직렬화한다", () => {
    expect(apiPath("/items", { category: "A-01", tags: ["a", "b"], empty: undefined })).toBe(
      "/api/v1/items?category=A-01&tags=a&tags=b",
    )
  })

  it("/api/ 로 시작하는 경로는 그대로 둔다", () => {
    expect(apiPath("/api/health")).toBe("/api/health")
  })
})

describe("fetchJson", () => {
  it("성공 응답 본문을 돌려준다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, { status: "ok" })))

    await expect(fetchJson("/api/health")).resolves.toEqual({ status: "ok" })
  })

  it("keepalive 는 요청한 경우에만 fetch 에 싣는다 — 페이지를 떠날 때의 정리 요청용", async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(jsonResponse(200, {})))
    vi.stubGlobal("fetch", fetchMock)

    await fetchJson("/upload-batches/5/discard", { method: "POST", keepalive: true })
    await fetchJson("/upload-batches/5")

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ method: "POST", keepalive: true })
    expect(fetchMock.mock.calls[1]?.[1]).toMatchObject({ method: "GET", keepalive: false })
  })

  it("오류 envelope 을 ApiError 로 세운다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, {
          error: {
            contract: "semantic-v1",
            family: "not_found",
            code: "resource_not_found",
            details: { criterionCode: "CR-ST-999" },
            diagnostic: { requestId: "abc123", message: "no row" },
          },
        }),
      ),
    )

    const error = await fetchJson("/items/1").catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({
      status: 404,
      family: "not_found",
      code: "resource_not_found",
      details: { criterionCode: "CR-ST-999" },
      diagnostic: { requestId: "abc123", message: "no row" },
    })
  })

  it("목록에 없는 code 는 unknown_error 로 두고 원문은 rawCode 에 남긴다", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(409, {
          error: {
            contract: "semantic-v1",
            family: "conflict",
            code: "brand_new_code",
            diagnostic: { requestId: "r1" },
          },
        }),
      ),
    )

    await expect(fetchJson("/items")).rejects.toMatchObject({
      status: 409,
      code: "unknown_error",
      rawCode: "brand_new_code",
    })
  })

  it("계약 밖 오류 본문은 unknown_error 로 둔다", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>502</html>", { status: 502 })))

    await expect(fetchJson("/items")).rejects.toMatchObject({ status: 502, code: "unknown_error" })
  })
})

describe("세션 만료(401) 처리", () => {
  it("인증 요청 밖의 401 은 등록된 핸들러를 부른다", async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(401, unauthorizedBody())))

    await expect(fetchJson("/items")).rejects.toMatchObject({ status: 401, code: "auth_required" })

    expect(handler).toHaveBeenCalledTimes(1)
  })

  it("/auth/* 의 401 은 화면 몫이라 핸들러를 부르지 않는다", async () => {
    const handler = vi.fn()
    setUnauthorizedHandler(handler)
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(401, unauthorizedBody())))

    await expect(fetchJson("/auth/me")).rejects.toMatchObject({ status: 401 })

    expect(handler).not.toHaveBeenCalled()
  })
})
