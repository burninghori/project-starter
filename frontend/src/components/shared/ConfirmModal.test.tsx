import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/api/transport"
import { OverlayHost } from "@/components/overlay/OverlayHost"
import { useOverlayStore } from "@/components/overlay/overlay-store"

import { openConfirmModal, openNoticeModal } from "./ConfirmModal"

afterEach(() => {
  useOverlayStore.setState({ stack: [] })
})

describe("openNoticeModal", () => {
  it("이유와 대안 문단을 보이고 확인으로 닫힌다 — 동작 버튼은 없다", async () => {
    const user = userEvent.setup()
    render(<OverlayHost />)
    openNoticeModal({
      title: "모듈 삭제",
      paragraphs: ["하위 항목 10건이 있어 삭제할 수 없습니다.", "「사용 안 함」으로 바꾸세요."],
    })

    const dialog = await screen.findByRole("dialog", { name: "모듈 삭제" })
    expect(dialog).toHaveTextContent("하위 항목 10건이 있어 삭제할 수 없습니다.")
    expect(dialog).toHaveTextContent("「사용 안 함」으로 바꾸세요.")
    expect(screen.queryByRole("button", { name: "삭제" })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "확인" }))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })
})

describe("openConfirmModal", () => {
  it("확인하면 동작을 실행하고 닫힌다", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    render(<OverlayHost />)
    openConfirmModal({
      title: "항목 삭제",
      message: "결제 항목을 삭제합니다. 되돌릴 수 없습니다.",
      confirmLabel: "삭제",
      tone: "danger",
      onConfirm,
    })

    expect(await screen.findByRole("dialog", { name: "항목 삭제" })).toHaveTextContent("되돌릴 수 없습니다")
    await user.click(screen.getByRole("button", { name: "삭제" }))

    expect(onConfirm).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("취소하면 동작 없이 닫힌다", async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn().mockResolvedValue(undefined)
    render(<OverlayHost />)
    openConfirmModal({
      title: "모듈 삭제",
      message: "지웁니다",
      confirmLabel: "삭제",
      tone: "danger",
      onConfirm,
    })

    await user.click(await screen.findByRole("button", { name: "취소" }))

    expect(onConfirm).not.toHaveBeenCalled()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("실패하면 닫지 않고 사유와 요청 ID 를 보인다", async () => {
    const user = userEvent.setup()
    const onConfirm = vi
      .fn()
      .mockRejectedValue(
        new ApiError(503, "unavailable", "database_unavailable", undefined, { requestId: "req-9" }),
      )
    render(<OverlayHost />)
    openConfirmModal({
      title: "항목 삭제",
      message: "지웁니다",
      confirmLabel: "삭제",
      tone: "danger",
      onConfirm,
    })

    await user.click(await screen.findByRole("button", { name: "삭제" }))

    const alert = await screen.findByRole("alert")
    expect(alert).toHaveTextContent("삭제하지 못했습니다")
    expect(alert).toHaveTextContent("데이터베이스에 연결할 수 없습니다")
    expect(alert).toHaveTextContent("요청 ID req-9")
    expect(screen.getByRole("dialog")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "삭제" })).toBeEnabled()
  })
})
