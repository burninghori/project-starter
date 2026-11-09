import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { describe, expect, it } from "vitest"

import { Tabs } from "./Tabs"

const ITEMS = [
  { value: "s1", label: "01 구조 정합성" },
  { value: "s2", label: "02 표준 용어" },
  { value: "s3", label: "03 내용 정합성" },
] as const

type Stage = (typeof ITEMS)[number]["value"]

function Harness() {
  const [value, setValue] = useState<Stage>("s1")
  return <Tabs label="검증 단계" items={ITEMS} value={value} onChange={setValue} variant="main" />
}

describe("Tabs", () => {
  it("누른 탭이 선택되고 선택된 탭만 Tab 순서에 든다", async () => {
    const user = userEvent.setup()
    render(<Harness />)

    await user.click(screen.getByRole("tab", { name: "02 표준 용어" }))

    expect(screen.getByRole("tab", { name: "02 표준 용어" })).toHaveAttribute("aria-selected", "true")
    expect(screen.getByRole("tab", { name: "01 구조 정합성" })).toHaveAttribute("tabindex", "-1")
  })

  it("←·→ 로 옆 탭으로 옮기며 고르고, 끝에서는 반대쪽으로 돈다", async () => {
    const user = userEvent.setup()
    render(<Harness />)

    screen.getByRole("tab", { name: "01 구조 정합성" }).focus()
    await user.keyboard("{ArrowLeft}")

    const last = screen.getByRole("tab", { name: "03 내용 정합성" })
    expect(last).toHaveAttribute("aria-selected", "true")
    expect(last).toHaveFocus()

    await user.keyboard("{ArrowRight}")
    expect(screen.getByRole("tab", { name: "01 구조 정합성" })).toHaveAttribute("aria-selected", "true")
  })
})
