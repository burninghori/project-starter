import { act, fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { FilterBar, FilterSearch, SubmitFilterSearch } from "./FilterBar"

const LABEL = "로그인 아이디 검색"

describe("FilterBar — 셀렉트 · 검색 뒤 보기 도구", () => {
  it("셀렉트는 줄에 펼치고, 보기 도구는 검색 바로 뒤, 동작 버튼은 빈칸 너머 오른쪽 끝이다", () => {
    render(
      <FilterBar
        count={<span>항목 3건</span>}
        search={<input aria-label="ID · 이름 검색" />}
        tools={<button type="button">모두 펼치기</button>}
        actions={<button type="button">종결 처리</button>}
      >
        <select aria-label="모듈" />
      </FilterBar>,
    )

    // 「필터」 단추로 여는 줄은 없다 — 셀렉트는 처음부터 보인다
    expect(screen.queryByRole("button", { name: /^필터/ })).not.toBeInTheDocument()
    const search = screen.getByRole("textbox", { name: "ID · 이름 검색" })
    expect(search.previousElementSibling).toBe(screen.getByRole("combobox", { name: "모듈" }))
    const tools = screen.getByRole("button", { name: "모두 펼치기" })
    expect(search.nextElementSibling).toBe(tools)
    // 보기 도구 다음은 빈칸, 그 너머에 동작 버튼
    expect(tools.nextElementSibling?.textContent).toBe("")
    expect(tools.nextElementSibling?.nextElementSibling).toContainElement(
      screen.getByRole("button", { name: "종결 처리" }),
    )
  })
})

describe("SubmitFilterSearch", () => {
  it("치는 동안에는 조건을 걸지 않고 Enter 로 건다", async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<SubmitFilterSearch label={LABEL} value="" onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(LABEL), "admin")
    expect(onSubmit).not.toHaveBeenCalled()

    await user.keyboard("{Enter}")
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith("admin")
  })

  it("돋보기 버튼으로도 건다", async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<SubmitFilterSearch label={LABEL} value="" onSubmit={onSubmit} />)

    await user.type(screen.getByLabelText(LABEL), "guest")
    await user.click(screen.getByRole("button", { name: `${LABEL} 실행` }))

    expect(onSubmit).toHaveBeenCalledWith("guest")
  })

  it("칸을 비우면 바로 조건을 푼다", async () => {
    const onSubmit = vi.fn()
    const user = userEvent.setup()
    render(<SubmitFilterSearch label={LABEL} value="admin" onSubmit={onSubmit} />)

    await user.clear(screen.getByLabelText(LABEL))

    expect(onSubmit).toHaveBeenCalledWith("")
  })

  it("바깥에서 조건이 바뀌면 입력칸도 따른다", () => {
    const { rerender } = render(<SubmitFilterSearch label={LABEL} value="admin" onSubmit={vi.fn()} />)

    rerender(<SubmitFilterSearch label={LABEL} value="" onSubmit={vi.fn()} />)

    expect(screen.getByLabelText(LABEL)).toHaveValue("")
  })
})

describe("FilterSearch — 자동완성식 화면 전용(0.3초 디바운스)", () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it("치는 동안에는 걸지 않고, 입력이 멈추고 0.3초 뒤 마지막 글자로 한 번 건다", () => {
    vi.useFakeTimers()
    const onChange = vi.fn()
    render(<FilterSearch label={LABEL} value="" onChange={onChange} />)
    const input = screen.getByLabelText(LABEL)

    fireEvent.change(input, { target: { value: "a" } })
    act(() => vi.advanceTimersByTime(200))
    fireEvent.change(input, { target: { value: "adm" } })
    act(() => vi.advanceTimersByTime(299))
    expect(onChange).not.toHaveBeenCalled()

    act(() => vi.advanceTimersByTime(1))
    expect(onChange).toHaveBeenCalledTimes(1)
    expect(onChange).toHaveBeenCalledWith("adm")
  })

  it("기다리는 중에 바깥에서 조건이 바뀌면(필터 초기화 등) 예약된 검색을 버린다", () => {
    vi.useFakeTimers()
    const onChange = vi.fn()
    const { rerender } = render(<FilterSearch label={LABEL} value="" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText(LABEL), { target: { value: "adm" } })
    act(() => vi.advanceTimersByTime(100))
    rerender(<FilterSearch label={LABEL} value="guest" onChange={onChange} />)
    act(() => vi.advanceTimersByTime(500))

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByLabelText(LABEL)).toHaveValue("guest")
  })

  it("그릴 때마다 새 함수를 넘겨도 기다리던 시간이 처음부터 다시 시작되지 않는다", () => {
    vi.useFakeTimers()
    const first = vi.fn()
    const second = vi.fn()
    const { rerender } = render(<FilterSearch label={LABEL} value="" onChange={first} />)

    fireEvent.change(screen.getByLabelText(LABEL), { target: { value: "adm" } })
    act(() => vi.advanceTimersByTime(200))
    rerender(<FilterSearch label={LABEL} value="" onChange={second} />)
    act(() => vi.advanceTimersByTime(100))

    expect(first).not.toHaveBeenCalled()
    expect(second).toHaveBeenCalledTimes(1)
    expect(second).toHaveBeenCalledWith("adm")
  })

  it("칸을 비우면 기다리지 않고 바로 푼다", async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(<FilterSearch label={LABEL} value="admin" onChange={onChange} />)

    await user.clear(screen.getByLabelText(LABEL))

    expect(onChange).toHaveBeenCalledWith("")
  })

  it("바깥에서 조건이 바뀌면 입력칸도 따른다", () => {
    const { rerender } = render(<FilterSearch label={LABEL} value="admin" onChange={vi.fn()} />)

    rerender(<FilterSearch label={LABEL} value="" onChange={vi.fn()} />)

    expect(screen.getByLabelText(LABEL)).toHaveValue("")
  })
})
