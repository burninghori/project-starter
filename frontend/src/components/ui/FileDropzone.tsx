import { Upload, X } from "lucide-react"
import { useState, type ChangeEvent, type DragEvent, type ReactNode } from "react"

import { cn } from "@/lib/cn"

import { IconButton } from "./Button"

interface FileDropzoneProps {
  /** `<input accept>` 값. 끌어다 놓은 파일은 브라우저가 거르지 않으므로 형식 검사는 받는 쪽이 한다 */
  accept: string
  /** 큰 줄 — 예: 「JSON 또는 ZIP 파일을 끌어다 놓으세요」 */
  title: string
  /** 작은 줄. 「파일 선택」 글자는 청록 밑줄로 보인다 — 예: 「· .json · .zip 혼합 가능 · 여러 파일 동시 등록」 */
  hint: ReactNode
  /** 드롭존 안 맨 아래 줄 — 예: 예상 파일명. 없으면 null */
  note: ReactNode | null
  onFiles: (files: File[]) => void
}

/**
 * 파일을 끌어다 놓거나 눌러서 고르는 자리. 여러 파일을 한 번에 받는다.
 * 같은 파일을 다시 고를 수 있게 고른 뒤 input 값을 비운다 — 선택 목록은 부르는 쪽이 소유한다.
 */
export function FileDropzone({ accept, title, hint, note, onFiles }: FileDropzoneProps) {
  const [dragging, setDragging] = useState(false)

  function onDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setDragging(true)
  }

  function onDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setDragging(false)
    onFiles(Array.from(event.dataTransfer.files))
  }

  function onChange(event: ChangeEvent<HTMLInputElement>) {
    const { files } = event.currentTarget
    if (files) onFiles(Array.from(files))
    event.currentTarget.value = ""
  }

  return (
    <label
      className={cn("app-dropzone flex flex-col items-center gap-1", dragging && "app-dropzone--active")}
      onDragOver={onDragOver}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
    >
      <Upload size={19} aria-hidden />
      <span className="app-dropzone__title">{title}</span>
      <span className="app-dropzone__hint">
        또는 <span className="app-dropzone__pick">파일 선택</span> {hint}
      </span>
      {note !== null && <span className="app-dropzone__hint mt-1">{note}</span>}
      <input type="file" className="sr-only" accept={accept} multiple onChange={onChange} />
    </label>
  )
}

/** 고른 파일 한 줄 — 이름(굵게) · 부가 정보 · 오른쪽 빼기 버튼 */
export function FileRow({
  name,
  detail,
  onRemove,
}: {
  name: string
  detail: ReactNode
  onRemove: () => void
}) {
  return (
    <div className="app-filerow flex items-center gap-2">
      <span className="font-semibold">{name}</span>
      <span className="min-w-0 flex-1 truncate">{detail}</span>
      <IconButton label={`${name} 빼기`} icon={<X size={14} aria-hidden />} onClick={onRemove} />
    </div>
  )
}
