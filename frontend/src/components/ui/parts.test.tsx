import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { Field, FormError, TextInput } from "./Field"
import { FilterBar, FilterCount, SubmitFilterSearch } from "./FilterBar"
import { BackBar, Card } from "./Layout"
import { ProgressBar } from "./ProgressBar"
import { StatFilterTile } from "./StatTile"
import { TagIdButton } from "./Tag"

/** 로직이 작은 공통 부품들 — 접근성 이름·상태·경계 동작만 확인한다 */

describe("Field", () => {
  it("라벨이 입력의 이름이 된다", () => {
    render(
      <Field label="버전" required={false} labelNote={null} hint={null} error={null}>
        {(control) => <TextInput {...control} placeholder="예) v0.5" />}
      </Field>,
    )

    const input = screen.getByRole("textbox", { name: "버전" })
    expect(input).not.toHaveAttribute("aria-describedby")
    expect(input).toHaveAttribute("aria-invalid", "false")
    expect(input).toHaveAttribute("aria-required", "false")
  })

  it("안내·오류 줄을 입력에 잇고, 오류면 입력을 오류로 표시한다", () => {
    render(
      <Field label="버전" required={false} labelNote={null} hint="예) v0.5" error="형식이 맞지 않습니다">
        {(control) => <TextInput {...control} />}
      </Field>,
    )

    const input = screen.getByRole("textbox", { name: "버전" })
    expect(input).toHaveAccessibleDescription("형식이 맞지 않습니다 예) v0.5")
    expect(input).toHaveAttribute("aria-invalid", "true")
    expect(screen.getByRole("alert")).toHaveTextContent("형식이 맞지 않습니다")
  })

  it("라벨 옆 문구는 「·」를 붙여 라벨 바로 뒤(입력 위)에 두고, 필수 「*」는 입력 이름에 섞지 않는다", () => {
    render(
      <Field label="코드" required labelNote="대문자 · 숫자 2~8자" hint="칸 아래 안내" error={null}>
        {(control) => <TextInput {...control} />}
      </Field>,
    )

    const input = screen.getByRole("textbox", { name: "코드" })
    const comesBefore = (a: Node, b: Node) =>
      (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
    // 라벨 → 라벨 옆 문구 → 입력 → 칸 아래 안내
    expect(comesBefore(screen.getByText("코드"), screen.getByText("· 대문자 · 숫자 2~8자"))).toBe(true)
    expect(comesBefore(screen.getByText("· 대문자 · 숫자 2~8자"), input)).toBe(true)
    expect(comesBefore(input, screen.getByText("칸 아래 안내"))).toBe(true)
    expect(input).toHaveAccessibleDescription("· 대문자 · 숫자 2~8자 칸 아래 안내")
    expect(input).toHaveAttribute("aria-required", "true")
    expect(screen.getByText("*")).toHaveAttribute("aria-hidden", "true")
  })
})

describe("FormError", () => {
  it("칸 오류와 같은 모양의 한 줄로 바로 읽힌다", () => {
    render(<FormError requestId={null}>서버에 연결하지 못했습니다</FormError>)

    const alert = screen.getByRole("alert")
    expect(alert).toHaveTextContent("서버에 연결하지 못했습니다")
    expect(alert).not.toHaveTextContent("요청 ID")
    expect(alert).toHaveClass("app-field__error")
  })

  it("서버가 처리하지 못한 실패는 같은 줄 끝에 요청 ID 를 붙인다", () => {
    render(<FormError requestId="req-77">서버에서 처리하지 못했습니다</FormError>)

    const alert = screen.getByRole("alert")
    expect(alert).toHaveTextContent("서버에서 처리하지 못했습니다 · 요청 ID req-77")
    expect(screen.getByText("req-77")).toHaveClass("app-mono")
  })
})

describe("FilterCount", () => {
  it("거르지 않았으면 전체, 걸렀으면 「전체 중 n건」", () => {
    const { rerender } = render(<FilterCount total={565} shown={565} />)
    expect(screen.getByText(/전체/)).toHaveTextContent("전체 565건")

    rerender(<FilterCount total={565} shown={148} />)
    expect(screen.getByText(/중/)).toHaveTextContent("565건 중 148건")
  })
})

describe("FilterBar", () => {
  /** 빈칸은 글자가 없는 요소다 — 검색 바로 앞·뒤 형제가 빈칸인지로 오른쪽 끝에 무엇이 붙는지 본다 */
  const isSpacer = (element: Element | null) =>
    element !== null && element.textContent === "" && element.tagName === "SPAN"

  function renderBar(actions: React.ReactNode) {
    render(
      <FilterBar
        count={<FilterCount total={37} shown={37} />}
        search={<SubmitFilterSearch label="모듈 · 도메인명 검색" value="" onSubmit={() => {}} />}
        tools={null}
        actions={actions}
      >
        <select aria-label="사용 여부" />
      </FilterBar>,
    )
    // 검색칸은 돋보기 단추와 함께 form 으로 감싸져 있다 — 필터 줄의 형제 관계는 그 form 으로 본다
    return screen.getByRole("search")
  }

  it("동작 버튼이 없어도 검색은 셀렉트 바로 뒤이고, 오른쪽 끝은 비운다", () => {
    const search = renderBar(null)

    expect(search.previousElementSibling).toBe(screen.getByRole("combobox", { name: "사용 여부" }))
    expect(search.nextElementSibling).toBeNull()
  })

  it("동작 버튼이 있으면 검색은 셀렉트 바로 뒤, 버튼이 오른쪽 끝이다 — 검색 · 빈칸 · 버튼", () => {
    const search = renderBar(<button type="button">모듈 추가</button>)

    expect(search.previousElementSibling).toBe(screen.getByRole("combobox", { name: "사용 여부" }))
    expect(isSpacer(search.nextElementSibling)).toBe(true)
    expect(search.nextElementSibling?.nextElementSibling).toContainElement(
      screen.getByRole("button", { name: "모듈 추가" }),
    )
  })
})

describe("StatFilterTile", () => {
  it("눌러서 거르고, 걸림 상태를 눌림으로 알린다", async () => {
    const onToggle = vi.fn()
    const user = userEvent.setup()
    render(
      <StatFilterTile
        label="실패"
        value={148}
        sub="26.2%"
        tone="danger"
        size="sm"
        pressed={true}
        onToggle={onToggle}
      />,
    )

    const tile = screen.getByRole("button", { name: /실패/ })
    expect(tile).toHaveAttribute("aria-pressed", "true")
    await user.click(tile)
    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})

describe("ProgressBar", () => {
  it("값을 0~100 으로 잘라 알린다", () => {
    render(<ProgressBar value={130} tone="ok" size="default" label="진행률" />)

    expect(screen.getByRole("progressbar", { name: "진행률" })).toHaveAttribute("aria-valuenow", "100")
  })
})

describe("BackBar", () => {
  it("갈 곳이 없는 쪽은 비활성으로 둔다", async () => {
    const onBack = vi.fn()
    const onNext = vi.fn()
    const user = userEvent.setup()
    render(<BackBar crumb="항목 › 분류" onBack={onBack} onPrev={null} onNext={onNext} />)

    expect(screen.getByRole("button", { name: "이전" })).toBeDisabled()
    await user.click(screen.getByRole("button", { name: "다음" }))
    await user.click(screen.getByRole("button", { name: "목록으로" }))
    expect(onNext).toHaveBeenCalledTimes(1)
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})

describe("Card", () => {
  it("제목이 있으면 머리줄을, 없으면 내용만 그린다", () => {
    const { rerender } = render(
      <Card title="항목별 결과" note="버전 v4" actions={null}>
        내용
      </Card>,
    )
    expect(screen.getByRole("heading", { name: "항목별 결과" })).toBeInTheDocument()

    rerender(
      <Card title={null} note={null} actions={null}>
        내용
      </Card>,
    )
    expect(screen.queryByRole("heading")).not.toBeInTheDocument()
  })
})

describe("TagIdButton", () => {
  it("상태와 ID 가 함께 버튼 이름이 된다", () => {
    render(<TagIdButton tone="warn" status="처리 중" id="ORD-0312" onClick={() => {}} />)

    expect(screen.getByRole("button", { name: "처리 중 ORD-0312" })).toBeInTheDocument()
  })
})
