import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { AccordionNote, AccordionPanel, AccordionRow, AccordionSide, ExpandAllButton } from "./Accordion"

describe("AccordionPanel", () => {
  it("머리에 제목 · 건수 · 오른쪽 동작을, 오른쪽 상자가 있으면 이름 · 값 줄을 그린다", () => {
    render(
      <table>
        <tbody>
          <AccordionRow colSpan={8}>
            <AccordionPanel
              title="실패 항목"
              count={2}
              actions={<button type="button">종결 처리</button>}
              side={
                <AccordionSide
                  items={[
                    { label: "등록일", value: "2026-11-05 10:20" },
                    { label: "해결책", value: "-" },
                  ]}
                />
              }
            >
              <AccordionNote>안내 한 줄</AccordionNote>
            </AccordionPanel>
          </AccordionRow>
        </tbody>
      </table>,
    )

    expect(screen.getByText("실패 항목")).toBeInTheDocument()
    expect(screen.getByText("2건")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "종결 처리" })).toBeInTheDocument()
    expect(screen.getByRole("cell")).toHaveAttribute("colspan", "8")
    // 오른쪽 상자 — 이름(dt)과 값(dd)
    expect(screen.getAllByRole("term").map((cell) => cell.textContent)).toEqual(["등록일", "해결책"])
    expect(screen.getAllByRole("definition").map((cell) => cell.textContent)).toEqual([
      "2026-11-05 10:20",
      "-",
    ])
    expect(screen.getByText("안내 한 줄").closest(".app-acc")).toHaveClass("app-acc--side")
  })

  it("오른쪽 상자가 없으면 비율 칸을 줄이지 않는다", () => {
    render(
      <AccordionPanel title="검사 항목" count={4} actions={null} side={null}>
        <AccordionNote>표</AccordionNote>
      </AccordionPanel>,
    )

    expect(screen.getByText("표").closest(".app-acc")).not.toHaveClass("app-acc--side")
    expect(screen.queryByRole("definition")).not.toBeInTheDocument()
  })
})

describe("ExpandAllButton", () => {
  it("이 쪽 줄이 모두 펼쳐져 있으면 「모두 접기」, 줄이 없으면 비활성", async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    const { rerender } = render(<ExpandAllButton allOpen={false} disabled={false} onToggle={onToggle} />)

    await user.click(screen.getByRole("button", { name: "모두 펼치기" }))
    expect(onToggle).toHaveBeenCalledTimes(1)

    rerender(<ExpandAllButton allOpen disabled={false} onToggle={onToggle} />)
    expect(screen.getByRole("button", { name: "모두 접기" })).toBeEnabled()

    rerender(<ExpandAllButton allOpen={false} disabled onToggle={onToggle} />)
    expect(screen.getByRole("button", { name: "모두 펼치기" })).toBeDisabled()
  })
})
