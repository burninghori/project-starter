import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { ComingSoonPage } from "./ComingSoonPage"

describe("ComingSoonPage", () => {
  it("제목은 메뉴 이름, 설명은 그 화면이 할 일 한 줄이고 준비 중임을 알린다", () => {
    render(<ComingSoonPage title="설정" summary="운영에 필요한 설정을 보고 바꿉니다" />)

    expect(screen.getByRole("heading", { level: 1, name: "설정" })).toBeInTheDocument()
    expect(screen.getByText("운영에 필요한 설정을 보고 바꿉니다")).toBeInTheDocument()
    expect(screen.getByText("준비 중인 화면입니다")).toBeInTheDocument()
  })
})
