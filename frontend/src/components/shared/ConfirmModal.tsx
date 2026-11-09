import { useState, type ReactNode } from "react"

import { ModalBody, ModalFooter } from "@/components/overlay/Modal"
import { openModal } from "@/components/overlay/overlay-store"
import { Button } from "@/components/ui/Button"

import { QueryErrorPanel } from "./QueryErrorPanel"

interface ConfirmModalOptions {
  title: string
  /** 무엇이 어떻게 되는지 한두 문장(영향이 여럿이면 문단 · 목록으로 묶은 내용). 되돌릴 수 없는 동작은 그 사실을 적는다 */
  message: ReactNode
  /** 확인 버튼 글자 — 동작 이름 그대로(「삭제」). 마침표 없음 */
  confirmLabel: string
  /** 비가역 동작(삭제)은 `danger`, 그 밖의 확인은 `primary` */
  tone: "danger" | "primary"
  /** 확인했을 때 할 일. 끝나면 모달이 닫히고, 던지면 모달 안에 사유가 보인다 */
  onConfirm: () => Promise<void>
}

/**
 * 확인 모달 — 브라우저 confirm 대신 쓴다(저장소 규칙 — 떠 있는 면은 모두 우리 모달). 동작이 끝날 때까지 버튼을 잠그고,
 * 실패하면 닫지 않고 사유(요청 ID 포함)를 보여 다시 시도하거나 취소할 수 있게 한다.
 */
export function openConfirmModal(options: ConfirmModalOptions): void {
  openModal({
    title: options.title,
    size: "default",
    render: (close) => <ConfirmModalContent {...options} close={close} />,
  })
}

interface NoticeModalOptions {
  title: string
  /** 문단들 — 첫 문단은 할 수 없는 이유, 다음 문단은 대신 할 수 있는 일. 문단 안의 `\n` 은 그 자리에서 줄을 바꾼다 */
  paragraphs: readonly [string, ...string[]]
}

/**
 * 안내 모달 — 지금 할 수 없는 동작의 이유와 대안을 보인다. 확인 버튼 하나뿐이다.
 * 삭제처럼 되돌릴 수 없는 동작은 버튼을 흐리게 하지 않고, 할 수 없을 때 누르면 이 모달을 띄운다(design-concept 4절 「예외」).
 */
export function openNoticeModal({ title, paragraphs }: NoticeModalOptions): void {
  openModal({
    title,
    size: "default",
    render: (close) => (
      <>
        <ModalBody>
          {/* 문단 사이 12px — 문단 안 줄(20px)과 확실히 구분돼 「한 칸 띄움」처럼 읽힌다 */}
          <div className="flex flex-col gap-3">
            {paragraphs.map((paragraph) => (
              <p key={paragraph} className="m-0 whitespace-pre-line">
                {paragraph}
              </p>
            ))}
          </div>
        </ModalBody>
        <ModalFooter note={null}>
          <Button variant="primary" size="md" onClick={close}>
            확인
          </Button>
        </ModalFooter>
      </>
    ),
  })
}

function ConfirmModalContent({
  message,
  confirmLabel,
  tone,
  onConfirm,
  close,
}: Omit<ConfirmModalOptions, "title"> & { close: () => void }) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function confirm() {
    setPending(true)
    setError(null)
    try {
      await onConfirm()
      close()
    } catch (caught) {
      setError(caught)
      setPending(false)
    }
  }

  return (
    <>
      <ModalBody>
        <div className="flex flex-col gap-3">
          {/* 문단 · 목록을 담을 수 있게 p 가 아니라 div 로 감싼다(p 안에 블록 요소는 HTML 규칙 위반) */}
          <div>{message}</div>
          {error !== null && <QueryErrorPanel error={error} title={`${confirmLabel}하지 못했습니다`} />}
        </div>
      </ModalBody>
      <ModalFooter note={null}>
        <Button variant="secondary" size="md" disabled={pending} onClick={close}>
          취소
        </Button>
        <Button variant={tone} size="md" disabled={pending} onClick={() => void confirm()}>
          {confirmLabel}
        </Button>
      </ModalFooter>
    </>
  )
}
