import { describe, expect, it } from "vitest"

import { PAGES } from "./pages-config"

/**
 * 화면 목록의 불변식만 본다. 메뉴 순서와 「준비 중」 표시는 router.test 가 본다 — 기능이 완성되는 PR 이
 * 그 메뉴를 열면서 그 테스트의 한 줄을 함께 고친다
 */
describe("pages-config", () => {
  it("경로는 / 로 시작하고 서로 겹치지 않는다", () => {
    const paths = PAGES.map((page) => page.path)

    expect(paths.every((path) => path.startsWith("/"))).toBe(true)
    expect(new Set(paths).size).toBe(paths.length)
  })
})
