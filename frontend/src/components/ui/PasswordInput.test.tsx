import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { useState } from "react"
import { describe, expect, it } from "vitest"

import { Field } from "./Field"
import { PasswordInput } from "./PasswordInput"

function Harness() {
  const [value, setValue] = useState("")
  return (
    <form onSubmit={(event) => event.preventDefault()}>
      <Field label="비밀번호" required={false} labelNote={null} hint="8자 이상" error={null}>
        {(control) => (
          <PasswordInput
            {...control}
            fieldLabel="비밀번호"
            autoComplete="current-password"
            value={value}
            onChange={(event) => setValue(event.target.value)}
          />
        )}
      </Field>
      <button type="submit">제출</button>
    </form>
  )
}

describe("PasswordInput", () => {
  it("보기 버튼으로 값을 보이고 숨기며, 누른 뒤에도 커서는 입력에 남는다", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const input = screen.getByLabelText("비밀번호")
    const toggle = screen.getByRole("button", { name: "비밀번호 보기" })

    await user.type(input, "secret-pw")
    expect(input).toHaveAttribute("type", "password")
    expect(toggle).toHaveAttribute("aria-pressed", "false")

    await user.click(toggle)
    expect(input).toHaveAttribute("type", "text")
    expect(toggle).toHaveAttribute("aria-pressed", "true")
    expect(input).toHaveFocus()

    await user.click(toggle)
    expect(input).toHaveAttribute("type", "password")
  })

  it("폼을 제출하면 다시 가린다", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const input = screen.getByLabelText("비밀번호")

    await user.click(screen.getByRole("button", { name: "비밀번호 보기" }))
    expect(input).toHaveAttribute("type", "text")

    fireEvent.submit(input.closest("form")!)
    expect(input).toHaveAttribute("type", "password")
  })

  it("Caps Lock 이 켜진 채 입력하면 경고를 보이고, 칸을 떠나면 숨긴다", async () => {
    const user = userEvent.setup()
    render(<Harness />)
    const input = screen.getByLabelText("비밀번호")

    await user.click(input)
    await user.keyboard("a")
    expect(screen.queryByText("Caps Lock 이 켜져 있습니다")).not.toBeInTheDocument()

    await user.keyboard("{CapsLock}a")
    expect(screen.getByText("Caps Lock 이 켜져 있습니다")).toBeInTheDocument()
    expect(input).toHaveAccessibleDescription("8자 이상 Caps Lock 이 켜져 있습니다")

    await user.tab()
    expect(screen.queryByText("Caps Lock 이 켜져 있습니다")).not.toBeInTheDocument()
  })

  it("자동 완성·붙여넣기를 막지 않고 맞춤법 검사·자동 대문자를 끈다", () => {
    render(<Harness />)
    const input = screen.getByLabelText("비밀번호")

    expect(input).toHaveAttribute("autocomplete", "current-password")
    expect(input).toHaveAttribute("spellcheck", "false")
    expect(input).toHaveAttribute("autocapitalize", "none")
    expect(input).not.toHaveAttribute("onpaste")
  })
})
