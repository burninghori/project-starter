import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useExpandedRows } from "./use-expanded-rows"

function setup(resetKey: string, initial: readonly string[] | null) {
  return renderHook(({ key, seed }) => useExpandedRows(key, seed), {
    initialProps: { key: resetKey, seed: initial },
  })
}

describe("useExpandedRows", () => {
  it("줄 하나를 펼치고 접는다", () => {
    const { result } = setup("7차", [])

    act(() => result.current.toggle("1"))
    expect(result.current.isOpen("1")).toBe(true)
    act(() => result.current.toggle("1"))
    expect(result.current.isOpen("1")).toBe(false)
  })

  it("처음 펼칠 줄은 데이터가 온 뒤 한 번만 정한다 — 그 뒤 접어도 다시 펼치지 않는다", () => {
    const { result, rerender } = setup("q=ORD-0012", null)
    expect(result.current.isOpen("12")).toBe(false)

    rerender({ key: "q=ORD-0012", seed: ["12"] })
    expect(result.current.isOpen("12")).toBe(true)

    act(() => result.current.toggle("12"))
    rerender({ key: "q=ORD-0012", seed: ["12"] })
    expect(result.current.isOpen("12")).toBe(false)
  })

  it("조건이 바뀌면 펼친 줄을 비우고 처음 펼칠 줄을 다시 정한다", () => {
    const { result, rerender } = setup("모듈 1", [])
    act(() => result.current.toggle("1"))

    rerender({ key: "모듈 2", seed: ["5"] })
    expect(result.current.isOpen("1")).toBe(false)
    expect(result.current.isOpen("5")).toBe(true)
  })

  it("모두 펼치기 / 모두 접기는 넘긴 키(이 쪽의 줄)만 바꾼다", () => {
    const { result } = setup("7차", [])
    act(() => result.current.toggle("다른 쪽"))

    expect(result.current.allOpen(["1", "2"])).toBe(false)
    act(() => result.current.toggleAll(["1", "2"]))
    expect(result.current.allOpen(["1", "2"])).toBe(true)

    act(() => result.current.toggleAll(["1", "2"]))
    expect(result.current.isOpen("1")).toBe(false)
    expect(result.current.isOpen("2")).toBe(false)
    // 이 쪽 밖의 펼친 줄은 그대로
    expect(result.current.isOpen("다른 쪽")).toBe(true)
    // 줄이 없으면 「모두 펼쳐짐」이 아니다
    expect(result.current.allOpen([])).toBe(false)
  })
})
