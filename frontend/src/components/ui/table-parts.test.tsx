import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ExpandMark, RowCheckbox, rowKeyHandler, SelectAllCheckbox, SelectedMark, SelectNone } from "./Table"

/** 표의 작은 조각 — 줄 키보드 도우미 · 선택 열 · 펼침 · 선택 표시 */

describe("rowKeyHandler", () => {
  // 키 처리만 본다 — 안의 버튼 클릭이 줄의 onClick 으로 올라가는 것은 DOM 동작이라 여기서는 onClick 을 달지 않는다
  function Row({ onRow, onButton }: { onRow: () => void; onButton: () => void }) {
    return (
      <table>
        <tbody>
          <tr tabIndex={0} aria-label="줄" onKeyDown={rowKeyHandler(onRow)}>
            <td>
              <button type="button" onClick={onButton}>
                안의 버튼
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    )
  }

  it("줄에 포커스가 있으면 Enter · Space 가 클릭과 같고, 안의 버튼에서 올라온 키는 줄을 누르지 않는다", async () => {
    const onRow = vi.fn()
    const onButton = vi.fn()
    const user = userEvent.setup()
    render(<Row onRow={onRow} onButton={onButton} />)

    screen.getByRole("row", { name: "줄" }).focus()
    await user.keyboard("{Enter}")
    await user.keyboard(" ")
    expect(onRow).toHaveBeenCalledTimes(2)

    screen.getByRole("button", { name: "안의 버튼" }).focus()
    await user.keyboard("{Enter}")
    expect(onButton).toHaveBeenCalledTimes(1)
    expect(onRow).toHaveBeenCalledTimes(2)
  })
})

describe("선택 열", () => {
  it("머리 체크는 일부만 골랐으면 일부 선택이고, 누르면 고른 상태를 알린다", async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    const { rerender } = render(
      <SelectAllCheckbox label="이 쪽 모두 선택" state="some" disabled={false} onChange={onChange} />,
    )

    const head = screen.getByRole("checkbox", { name: "이 쪽 모두 선택" })
    expect(head).toBePartiallyChecked()
    await user.click(head)
    expect(onChange).toHaveBeenLastCalledWith(true)

    rerender(<SelectAllCheckbox label="이 쪽 모두 선택" state="all" disabled={false} onChange={onChange} />)
    expect(head).toBeChecked()
    expect(head).not.toBePartiallyChecked()

    rerender(<SelectAllCheckbox label="이 쪽 모두 선택" state="none" disabled onChange={onChange} />)
    expect(head).toBeDisabled()
  })

  it("행 체크를 눌러도 펼치는 줄의 클릭으로 번지지 않는다", async () => {
    const onRow = vi.fn()
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <table>
        <tbody>
          <tr onClick={onRow}>
            <td>
              <RowCheckbox label="ORD-0012 선택" checked={false} onChange={onChange} />
            </td>
            <td>
              <SelectNone />
            </td>
          </tr>
        </tbody>
      </table>,
    )

    await user.click(screen.getByRole("checkbox", { name: "ORD-0012 선택" }))
    expect(onChange).toHaveBeenCalledWith(true)
    expect(onRow).not.toHaveBeenCalled()
    expect(screen.getByText("-")).toBeInTheDocument()
  })
})

describe("펼침 · 선택 표시(app-ui-spec 8절 D66)", () => {
  // 장식이라 역할 · 이름이 없다 — 그려진 표시(모양은 CSS)와 그 상태 클래스를 본다
  function iconOf(container: HTMLElement): Element {
    const icon = container.firstElementChild
    if (icon === null) throw new Error("표시가 그려지지 않았다")
    return icon
  }

  it("펼침 표시는 화면 읽기에서 빠지고, 펼쳤을 때만 아래를 가리키게 돌린다", () => {
    const closed = iconOf(render(<ExpandMark open={false} />).container)
    expect(closed).toHaveAttribute("aria-hidden", "true")
    expect(closed).toHaveClass("app-table__toggle")
    expect(closed).not.toHaveClass("app-table__toggle--open")

    const open = iconOf(render(<ExpandMark open />).container)
    expect(open).toHaveClass("app-table__toggle", "app-table__toggle--open")
  })

  it("선택 표시는 고른 행에만 보이고, 고르지 않은 행에도 같은 자리를 남긴다 — 고를 때 글자가 밀리지 않게", () => {
    const selected = iconOf(render(<SelectedMark selected />).container)
    expect(selected).toHaveAttribute("aria-hidden", "true")
    expect(selected).toHaveClass("app-table__mark")
    expect(selected).not.toHaveClass("app-table__mark--off")

    // 숨김(visibility)은 자리를 남긴다 — 표시를 아예 그리지 않으면 고를 때 글자가 밀린다
    const unselected = iconOf(render(<SelectedMark selected={false} />).container)
    expect(unselected).toHaveClass("app-table__mark", "app-table__mark--off")
  })
})
