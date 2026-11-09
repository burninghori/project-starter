import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { Pager } from "./Pager"

describe("Pager", () => {
  it("보이는 범위와 쪽 번호를 보이고, 첫 쪽에서는 이전을 막는다", async () => {
    const onPageChange = vi.fn()
    const user = userEvent.setup()
    render(
      <Pager page={1} pageSize={10} total={565} onPageChange={onPageChange} onPageSizeChange={() => {}} />,
    )

    expect(screen.getByText("1–10 표시")).toBeInTheDocument()
    expect(screen.getByText("1 / 57")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "이전" })).toBeDisabled()

    await user.click(screen.getByRole("button", { name: "다음" }))
    expect(onPageChange).toHaveBeenCalledWith(2)
  })

  it("마지막 쪽에서는 다음을 막는다", () => {
    render(<Pager page={3} pageSize={20} total={45} onPageChange={() => {}} onPageSizeChange={() => {}} />)

    expect(screen.getByText("41–45 표시")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "다음" })).toBeDisabled()
  })

  it("쪽 크기를 바꾸면 보던 위치가 들어 있는 쪽을 함께 넘긴다", async () => {
    const onPageSizeChange = vi.fn()
    const user = userEvent.setup()
    render(
      <Pager
        page={5}
        pageSize={10}
        total={565}
        onPageChange={() => {}}
        onPageSizeChange={onPageSizeChange}
      />,
    )

    await user.selectOptions(screen.getByRole("combobox", { name: "표시 건수" }), "20건씩")

    expect(onPageSizeChange).toHaveBeenCalledWith(20, 3)
  })
})
