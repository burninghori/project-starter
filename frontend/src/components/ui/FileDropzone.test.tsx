import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { FileDropzone, FileRow } from "./FileDropzone"

describe("FileDropzone", () => {
  it("고른 파일을 모두 넘기고, 같은 파일을 다시 고를 수 있게 입력을 비운다", async () => {
    const onFiles = vi.fn()
    const user = userEvent.setup()
    render(
      <FileDropzone
        accept=".json,.zip"
        title="JSON 또는 ZIP 파일을 끌어다 놓으세요"
        hint="· .json · .zip 혼합 가능"
        note={null}
        onFiles={onFiles}
      />,
    )

    const input = screen.getByLabelText(/JSON 또는 ZIP 파일을 끌어다 놓으세요/) as HTMLInputElement
    const a = new File(["{}"], "a.json", { type: "application/json" })
    const b = new File(["{}"], "b.json", { type: "application/json" })
    await user.upload(input, [a, b])

    expect(onFiles).toHaveBeenCalledWith([a, b])
    expect(input.value).toBe("")
  })
})

describe("FileDropzone 안내 줄", () => {
  it("note 를 드롭존 안 맨 아래 줄로 보인다 — 끌어다 놓는 자리와 같은 칸이라 함께 읽힌다", () => {
    render(
      <FileDropzone
        accept=".json"
        title="JSON 파일을 끌어다 놓으세요"
        hint="· 파일 하나"
        note="예상 파일명 report-….pdf"
        onFiles={vi.fn()}
      />,
    )

    expect(screen.getByLabelText(/JSON 파일을 끌어다 놓으세요/)).toHaveAccessibleName(
      /예상 파일명 report-….pdf/,
    )
  })
})

describe("FileRow", () => {
  it("파일 이름으로 빼기 버튼을 찾을 수 있다", async () => {
    const onRemove = vi.fn()
    const user = userEvent.setup()
    render(<FileRow name="report-2026.pdf" detail="검사 통과" onRemove={onRemove} />)

    await user.click(screen.getByRole("button", { name: "report-2026.pdf 빼기" }))
    expect(onRemove).toHaveBeenCalledTimes(1)
  })
})
