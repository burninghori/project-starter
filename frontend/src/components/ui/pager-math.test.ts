import { describe, expect, it } from "vitest"

import { pageAfterResize, pageWindow, toPageSize } from "./pager-math"

describe("pageWindow", () => {
  it.each([
    // page, size, total → page, pageCount, first, last
    [1, 10, 565, { page: 1, pageCount: 57, first: 1, last: 10 }],
    [57, 10, 565, { page: 57, pageCount: 57, first: 561, last: 565 }],
    [3, 20, 45, { page: 3, pageCount: 3, first: 41, last: 45 }],
    [1, 10, 0, { page: 1, pageCount: 1, first: 0, last: 0 }],
  ])("%i쪽 · %i건씩 · 전체 %i건", (page, size, total, expected) => {
    expect(pageWindow(page, size, total)).toEqual(expected)
  })

  it("필터로 건수가 줄어 쪽이 넘치면 마지막 쪽으로 붙인다", () => {
    expect(pageWindow(9, 10, 25)).toMatchObject({ page: 3, first: 21, last: 25 })
  })

  it("잘못된 입력은 오류 — 조용히 고치지 않는다", () => {
    expect(() => pageWindow(0, 10, 5)).toThrow()
    expect(() => pageWindow(1, 0, 5)).toThrow()
    expect(() => pageWindow(1, 10, -1)).toThrow()
  })
})

describe("pageAfterResize", () => {
  it("보던 쪽의 첫 행이 들어 있는 쪽으로 간다", () => {
    // 10건씩 5쪽 = 41번째 행부터 → 20건씩이면 3쪽(41~60)
    expect(pageAfterResize(5, 10, 20)).toBe(3)
    // 50건씩 2쪽 = 51번째 행 → 10건씩이면 6쪽
    expect(pageAfterResize(2, 50, 10)).toBe(6)
    expect(pageAfterResize(1, 10, 100)).toBe(1)
  })
})

describe("toPageSize", () => {
  it("선택지 값만 받는다", () => {
    expect(toPageSize("20")).toBe(20)
    expect(() => toPageSize("25")).toThrow()
  })
})
