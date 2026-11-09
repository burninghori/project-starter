import {
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react"

import { cn } from "@/lib/cn"

/** 입력 요소에 그대로 펼쳐 넣는 연결 값 — 라벨과 잇는 id · 라벨 옆 문구와 칸 아래 줄(안내·오류) id · 오류 여부 · 필수 여부 */
export interface FieldControl {
  id: string
  "aria-describedby": string | undefined
  "aria-invalid": boolean
  "aria-required": boolean
}

/**
 * 라벨 + 입력 한 칸 + 칸 아래 줄(app-ui-spec 5절 「입력」). 칸 사이 간격은 부르는 쪽 배치가 정한다(12px).
 * `children` 은 `FieldControl` 을 받아 입력을 그린다 — `<TextInput {...control} />` 처럼 펼치면 라벨을 눌러도 입력에 포커스가 가고,
 * 라벨 옆 문구·칸 아래 줄이 화면 낭독기에 이어지며(`aria-describedby`), 오류면 칸 테두리가 적색이 된다(`aria-invalid`).
 * - `required`: 라벨 뒤 적색 「*」. 화면 낭독기에는 `aria-required` 로 알린다. 잠긴 칸이면 false.
 * - `labelNote`: 라벨 옆 보조 문구 — 칸의 상태나 짧은 제약(「수정 불가」·「대문자 · 숫자 2~8자」). 앞의 「·」는 이 부품이 붙인다.
 *   라벨 요소 밖에 두어 입력의 이름은 라벨 글자 그대로다.
 * - `hint`: 칸 아래 안내 — 문장으로 된 입력 규칙·설명. `error`: 그 칸의 오류 한 줄(입력 바로 아래).
 * 없는 자리는 null.
 */
export function Field({
  label,
  required,
  labelNote,
  hint,
  error,
  children,
}: {
  label: string
  required: boolean
  labelNote: string | null
  hint: ReactNode
  error: string | null
  children: (control: FieldControl) => ReactNode
}) {
  const controlId = useId()
  const noteId = `${controlId}-note`
  const hintId = `${controlId}-hint`
  const errorId = `${controlId}-error`
  const describedBy = [
    error !== null ? errorId : null,
    labelNote !== null ? noteId : null,
    hint !== null ? hintId : null,
  ]
    .filter((id) => id !== null)
    .join(" ")
  return (
    <div className="flex flex-col gap-[5px]">
      <div className="flex flex-wrap items-baseline gap-x-1">
        <label htmlFor={controlId} className="app-field__label">
          {label}
          {required && (
            <span className="app-field__required" aria-hidden="true">
              *
            </span>
          )}
        </label>
        {labelNote !== null && (
          <span id={noteId} className="app-field__label-note">
            · {labelNote}
          </span>
        )}
      </div>
      {children({
        id: controlId,
        "aria-describedby": describedBy === "" ? undefined : describedBy,
        "aria-invalid": error !== null,
        "aria-required": required,
      })}
      {error !== null && (
        <p id={errorId} className="app-field__error" role="alert">
          {error}
        </p>
      )}
      {hint !== null && (
        <div id={hintId} className="app-field__hint">
          {hint}
        </div>
      )}
    </div>
  )
}

/**
 * 폼 오류 한 줄 — 어느 칸에도 속하지 않는 오류(로그인 실패·연결 실패·저장 실패)를 주 버튼 바로 위에 둔다.
 * 칸 아래 오류(`Field` 의 `error`)와 같은 빨간 글자 한 줄이고 상자로 감싸지 않는다(app-ui-spec 5절 「입력」).
 * `requestId` 는 서버가 처리하지 못한 실패의 요청 ID — 같은 줄 끝에 붙어 문의할 때 서버 로그와 맞춰 볼 수 있다.
 * 없으면 null(실패를 이 모양으로 바꾸는 것은 `api/error-messages` 의 `formFailure`).
 */
export function FormError({ children, requestId }: { children: ReactNode; requestId: string | null }) {
  return (
    <p className="app-field__error" role="alert">
      {children}
      {requestId !== null && (
        <>
          {" · 요청 ID "}
          <span className="app-mono">{requestId}</span>
        </>
      )}
    </p>
  )
}

/** 한 줄 입력. 읽기 전용이면 올림 면 바탕에 회색 글자로 보인다(편집 칸과 구분) */
export function TextInput({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("app-input", className)} {...props} />
}

export function SelectInput({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("app-input", className)} {...props} />
}

/** 여러 줄 입력. 최소 높이 66px, 세로로만 늘린다 */
export function TextArea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn("app-input app-input--multiline", className)} {...props} />
}
