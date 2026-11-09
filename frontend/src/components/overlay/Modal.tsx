import { X } from "lucide-react"
import { useEffect, useId, type ReactNode } from "react"

import { IconButton } from "@/components/ui/Button"
import { cn } from "@/lib/cn"

import type { ModalSize } from "./overlay-store"

interface ModalProps {
  title: string
  size: ModalSize
  /**
   * Esc 가 이 모달을 닫는가. 겹친 모달은 맨 위 하나만 true 다(`OverlayHost` 가 정한다) — 삭제 확인 위에서 Esc 를 누르면
   * 확인만 닫히고 아래 팝업은 남는다. 혼자 뜨는 모달은 true.
   */
  escapeCloses: boolean
  onClose: () => void
  /** `ModalBody` · `ModalFooter` 를 조합한 내용 */
  children: ReactNode
}

/**
 * 모달 셸 — 머리(제목 + ✕)만 그리고, 본문·바닥은 내용 쪽이 `ModalBody`·`ModalFooter` 로 조합한다.
 * 바닥 버튼이 본문의 입력 상태를 따르는 경우가 많아(파일을 골라야 등록 활성) 둘을 한 컴포넌트가 소유하게 한다.
 *
 * 닫는 길은 우상단 ✕ 와 Esc 둘이다. 바깥(배경) 클릭으로는 닫지 않는다 — 입력 중인 내용을 실수로 잃지 않게 한다.
 */
export function Modal({ title, size, escapeCloses, onClose, children }: ModalProps) {
  const titleId = useId()

  useEffect(() => {
    if (!escapeCloses) return
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [escapeCloses, onClose])

  return (
    <div className="app-backdrop">
      <div
        className={cn("app-modal", size === "wide" && "app-modal--wide")}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className="app-modal__head">
          <h2 id={titleId} className="app-modal__title">
            {title}
          </h2>
          <IconButton label="닫기" icon={<X size={18} aria-hidden />} onClick={onClose} />
        </header>
        {children}
      </div>
    </div>
  )
}

/** 모달 본문 — 넘치면 여기만 스크롤된다 */
export function ModalBody({ children }: { children: ReactNode }) {
  return <div className="app-modal__body">{children}</div>
}

/**
 * 모달 바닥 — 왼쪽에 안내 한 줄(`note`), 오른쪽에 버튼. 주 버튼을 맨 오른쪽에 두고, 삭제 같은 비가역 동작은
 * 버튼 줄 맨 앞(취소 왼쪽)에 위험 버튼으로 둔다(app-shell-spec 6절 「모달 치수」). 안내가 없는 바닥이면 `note={null}` 로 명시한다.
 */
export function ModalFooter({ note, children }: { note: ReactNode; children: ReactNode }) {
  return (
    <footer className="app-modal__foot">
      {note !== null && <span className="app-modal__foot-note">{note}</span>}
      {children}
    </footer>
  )
}

/**
 * 모달 구획 카드 — 큰 모달(여러 건 처리 등)의 본문을 나눈다(app-ui-spec 5절 「구조」). 머리줄은 제목 · 건수 · 오른쪽 작은 버튼
 * (「대상 목록 보기 ↔ 목록 접기」 등). 건수 · 버튼이 없으면 null.
 */
export function ModalSection({
  title,
  count,
  actions,
  children,
}: {
  title: string
  count: number | null
  actions: ReactNode
  children: ReactNode
}) {
  const titleId = useId()
  return (
    <section className="app-modal-section" aria-labelledby={titleId}>
      <div className="app-modal-section__head">
        <h3 id={titleId} className="app-modal-section__title">
          {title}
        </h3>
        {count !== null && <span className="app-modal-section__count">{count.toLocaleString()}건</span>}
        {actions !== null && <div className="ml-auto flex items-center gap-2">{actions}</div>}
      </div>
      <div className="app-modal-section__body">{children}</div>
    </section>
  )
}
