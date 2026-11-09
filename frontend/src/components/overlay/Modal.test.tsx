import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { Modal, ModalBody, ModalFooter } from "./Modal"
import { OverlayHost } from "./OverlayHost"
import { openModal, useOverlayStore } from "./overlay-store"

afterEach(() => {
  useOverlayStore.setState({ stack: [] })
})

describe("Modal", () => {
  it("제목을 대화상자 이름으로 쓴다", () => {
    render(
      <Modal title="항목 추가" size="default" escapeCloses onClose={() => {}}>
        <ModalBody>본문</ModalBody>
      </Modal>,
    )

    expect(screen.getByRole("dialog", { name: "항목 추가" })).toBeInTheDocument()
  })

  it("✕ 버튼과 Esc 로 닫는다", async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(
      <Modal title="항목 추가" size="default" escapeCloses onClose={onClose}>
        <ModalBody>본문</ModalBody>
      </Modal>,
    )

    await user.click(screen.getByRole("button", { name: "닫기" }))
    await user.keyboard("{Escape}")

    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it("바닥은 안내와 버튼을 함께 보이고, 안내 없이도 쓸 수 있다", () => {
    const { rerender } = render(
      <ModalFooter note="등록 이력에 등록자와 일시가 기록됩니다">
        <button type="button">등록</button>
      </ModalFooter>,
    )
    expect(screen.getByText("등록 이력에 등록자와 일시가 기록됩니다")).toBeInTheDocument()

    rerender(
      <ModalFooter note={null}>
        <button type="button">닫기</button>
      </ModalFooter>,
    )
    expect(screen.getByRole("contentinfo")).toHaveTextContent("닫기")
  })

  it("openModal 로 연 모달을 OverlayHost 가 그리고, 내용의 close 로 닫힌다", async () => {
    const user = userEvent.setup()
    render(<OverlayHost />)

    openModal({
      title: "버전별 현황",
      size: "wide",
      render: (close) => (
        <>
          <ModalBody>표</ModalBody>
          <ModalFooter note={null}>
            <button type="button" onClick={close}>
              확인
            </button>
          </ModalFooter>
        </>
      ),
    })

    expect(await screen.findByRole("dialog", { name: "버전별 현황" })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "확인" }))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("겹친 모달에서 Esc 는 맨 위 하나만 닫는다", async () => {
    const user = userEvent.setup()
    render(<OverlayHost />)
    openModal({ title: "도메인 수정", size: "default", render: () => <ModalBody>폼</ModalBody> })
    openModal({ title: "도메인 삭제", size: "default", render: () => <ModalBody>확인</ModalBody> })
    expect(await screen.findAllByRole("dialog")).toHaveLength(2)

    await user.keyboard("{Escape}")

    expect(screen.queryByRole("dialog", { name: "도메인 삭제" })).not.toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "도메인 수정" })).toBeInTheDocument()
    await user.keyboard("{Escape}")
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })
})
