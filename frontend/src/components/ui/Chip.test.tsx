import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { Chip, ChipBar, ChipSeparator } from "./Chip"

describe("Chip", () => {
  it("이름과 건수를 보이고, 걸림 상태를 눌림으로 알린다", async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(
      <Chip
        label="실패"
        count={1482}
        countTone="plain"
        pressed={true}
        disabled={false}
        axis="main"
        onToggle={onToggle}
      />,
    )

    const chip = screen.getByRole("button", { name: "실패 1,482" })
    expect(chip).toHaveAttribute("aria-pressed", "true")

    await user.click(chip)
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it("고를 수 없으면 흐리게 두고 누를 수 없다 — 숨기지 않는다", async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(
      <Chip
        label="확인 필요"
        count={0}
        countTone="plain"
        pressed={false}
        disabled={true}
        axis="main"
        onToggle={onToggle}
      />,
    )

    const chip = screen.getByRole("button", { name: "확인 필요 0" })
    expect(chip).toBeDisabled()
    await user.click(chip)
    expect(onToggle).not.toHaveBeenCalled()
  })

  it("칩 줄은 오른쪽 끝에 실행 버튼 등을 둔다", () => {
    render(
      <ChipBar end={<button type="button">01 단계 전량 검증 실행</button>}>
        <Chip
          label="전체"
          count={10}
          countTone="plain"
          pressed={false}
          disabled={false}
          axis="main"
          onToggle={() => {}}
        />
        <ChipSeparator />
        <Chip
          label="미처리 항목"
          count={5}
          countTone="plain"
          pressed={false}
          disabled={false}
          axis="subset"
          onToggle={() => {}}
        />
      </ChipBar>,
    )

    // 칩 둘 + 오른쪽 끝 버튼 하나
    expect(screen.getAllByRole("button")).toHaveLength(3)
    expect(screen.getByRole("button", { name: "01 단계 전량 검증 실행" })).toBeInTheDocument()
  })
})
