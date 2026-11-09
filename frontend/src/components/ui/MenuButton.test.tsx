import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { MenuButton } from "./MenuButton"

const TRIGGER = "홍길동 · admin"

/** 항목 셋 + 메뉴 뒤의 다음 요소(Tab 이동 확인용) */
function renderMenu() {
  const onResolve = vi.fn()
  const onFalse = vi.fn()
  const onExclude = vi.fn()
  render(
    <>
      <MenuButton
        label={TRIGGER}
        variant="secondary"
        size="sm"
        align="end"
        items={[
          { label: "해결", onSelect: onResolve },
          { label: "오탐", onSelect: onFalse },
          { label: "대상 제외", onSelect: onExclude },
        ]}
      />
      <button type="button">다음 요소</button>
    </>,
  )
  return { onResolve, onFalse, onExclude, trigger: screen.getByRole("button", { name: TRIGGER }) }
}

describe("MenuButton", () => {
  it("닫혀 있으면 메뉴가 없고, 트리거는 메뉴 버튼임을 알린다", () => {
    const { trigger } = renderMenu()

    expect(trigger).toHaveAttribute("aria-haspopup", "menu")
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(trigger).not.toHaveAttribute("aria-controls")
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("클릭으로 열면 메뉴가 트리거 이름으로 불리고 첫 항목에 포커스가 간다", async () => {
    const user = userEvent.setup()
    const { trigger } = renderMenu()

    await user.click(trigger)

    const menu = screen.getByRole("menu", { name: TRIGGER })
    expect(screen.getByRole("menuitem", { name: "해결" })).toHaveFocus()
    expect(trigger).toHaveAttribute("aria-expanded", "true")
    expect(trigger).toHaveAttribute("aria-controls", menu.id)
  })

  it("항목을 누르면 그 동작이 한 번 불리고, 닫히며 포커스는 트리거로 돌아온다", async () => {
    const user = userEvent.setup()
    const { trigger, onFalse, onResolve } = renderMenu()

    await user.click(trigger)
    await user.click(screen.getByRole("menuitem", { name: "오탐" }))

    expect(onFalse).toHaveBeenCalledTimes(1)
    expect(onResolve).not.toHaveBeenCalled()
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it("↓ 로 열고 Enter 로 고른다", async () => {
    const user = userEvent.setup()
    const { trigger, onResolve } = renderMenu()

    trigger.focus()
    await user.keyboard("{ArrowDown}")
    expect(screen.getByRole("menuitem", { name: "해결" })).toHaveFocus()

    await user.keyboard("{Enter}")
    expect(onResolve).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("Space 로도 고른다", async () => {
    const user = userEvent.setup()
    const { trigger, onResolve } = renderMenu()

    trigger.focus()
    await user.keyboard("{ArrowDown}")
    await user.keyboard("[Space]")

    expect(onResolve).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  })

  it("↑ 로 열면 마지막 항목, ↓↑ 는 끝에서 반대쪽으로 돌고 Home·End 는 처음·끝으로 간다", async () => {
    const user = userEvent.setup()
    const { trigger } = renderMenu()
    const item = (name: string) => screen.getByRole("menuitem", { name })

    trigger.focus()
    await user.keyboard("{ArrowUp}")
    expect(item("대상 제외")).toHaveFocus()

    await user.keyboard("{ArrowDown}")
    expect(item("해결")).toHaveFocus()
    await user.keyboard("{ArrowUp}")
    expect(item("대상 제외")).toHaveFocus()
    await user.keyboard("{Home}")
    expect(item("해결")).toHaveFocus()
    await user.keyboard("{End}")
    expect(item("대상 제외")).toHaveFocus()
  })

  it("Esc 로 닫히고 포커스는 트리거로 돌아온다 — 아무 동작도 불리지 않는다", async () => {
    const user = userEvent.setup()
    const { trigger, onResolve, onFalse, onExclude } = renderMenu()

    await user.click(trigger)
    await user.keyboard("{Escape}")

    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(onResolve).not.toHaveBeenCalled()
    expect(onFalse).not.toHaveBeenCalled()
    expect(onExclude).not.toHaveBeenCalled()
  })

  it("바깥을 누르면 닫힌다", async () => {
    const user = userEvent.setup()
    const { trigger, onResolve } = renderMenu()

    await user.click(trigger)
    await user.click(document.body)

    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(onResolve).not.toHaveBeenCalled()
  })

  it("트리거를 다시 누르면 닫힌다", async () => {
    const user = userEvent.setup()
    const { trigger } = renderMenu()

    await user.click(trigger)
    await user.click(trigger)

    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(trigger).toHaveAttribute("aria-expanded", "false")
  })

  it("Tab 은 메뉴를 닫고 트리거 다음 요소로 간다", async () => {
    const user = userEvent.setup()
    const { trigger } = renderMenu()

    await user.click(trigger)
    await user.tab()

    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "다음 요소" })).toHaveFocus()
  })

  it("한 화면에 메뉴가 둘이어도 각자 열리고 id 가 겹치지 않는다", async () => {
    const user = userEvent.setup()
    render(
      <>
        <MenuButton
          label="첫째"
          variant="secondary"
          size="sm"
          align="start"
          items={[{ label: "가", onSelect: () => {} }]}
        />
        <MenuButton
          label="둘째"
          variant="secondary"
          size="sm"
          align="end"
          items={[{ label: "나", onSelect: () => {} }]}
        />
      </>,
    )

    await user.click(screen.getByRole("button", { name: "둘째" }))

    const menus = screen.getAllByRole("menu")
    expect(menus).toHaveLength(1)
    expect(menus[0]).toHaveAccessibleName("둘째")
    expect(screen.getByRole("button", { name: "첫째" })).not.toHaveAttribute("aria-controls")
  })
})
