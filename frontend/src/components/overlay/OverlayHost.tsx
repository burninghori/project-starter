import { Modal } from "./Modal"
import { useOverlayStore } from "./overlay-store"

/** 열린 모달을 스택 순서대로 그린다. 앱 셸에 한 번만 둔다. Esc 는 맨 위 모달만 닫는다. */
export function OverlayHost() {
  const stack = useOverlayStore((state) => state.stack)
  const close = useOverlayStore((state) => state.close)

  return (
    <>
      {stack.map((entry, index) => {
        const onClose = () => close(entry.id)
        return (
          <Modal
            key={entry.id}
            title={entry.title}
            size={entry.size}
            escapeCloses={index === stack.length - 1}
            onClose={onClose}
          >
            {entry.render(onClose)}
          </Modal>
        )
      })}
    </>
  )
}
