import { useId, type ReactNode } from "react"

/**
 * 체크박스 · 라디오 — 브라우저 기본 모양에 강조색, 16px, 라벨 11.5 와 간격 6(app-ui-spec 5절 「체크박스 · 라디오」).
 * `RadioRow` · `CheckRow` 는 왼쪽 라벨 열(52px)을 맞춘 한 줄이다 — 팝업 폼의 심각도 · 차단 · 상태 같은 선택 줄.
 */

const LABEL_COLUMN = "app-field__label w-[52px] shrink-0"

export function Radio({
  name,
  checked,
  disabled,
  onChange,
  children,
}: {
  name: string
  checked: boolean
  /** 잠긴 값(바꿀 수 없는 선택) */
  disabled: boolean
  onChange: () => void
  children: ReactNode
}) {
  return (
    <label className="app-choice">
      <input type="radio" name={name} checked={checked} disabled={disabled} onChange={onChange} />
      {children}
    </label>
  )
}

export function Checkbox({
  checked,
  disabled,
  onChange,
  children,
}: {
  checked: boolean
  disabled: boolean
  onChange: (checked: boolean) => void
  children: ReactNode
}) {
  return (
    <label className="app-choice">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      {children}
    </label>
  )
}

/** 선택지 라벨 뒤의 짧은 보조 문구(회색) */
export function ChoiceNote({ children }: { children: ReactNode }) {
  return <span className="app-choice__note">{children}</span>
}

/** 라벨 열 + 라디오 묶음 한 줄 */
export function RadioRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      <span className={LABEL_COLUMN}>{label}</span>
      {children}
    </div>
  )
}

/** 라벨 열 + 체크박스 하나. `hint` 는 라벨에 마우스를 올리면 보인다 */
export function CheckRow({
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  label: string
  hint: string
  checked: boolean
  disabled: boolean
  onChange: (checked: boolean) => void
}) {
  const id = useId()
  return (
    <div className="flex items-center gap-x-4">
      <label htmlFor={id} className={LABEL_COLUMN} title={hint}>
        {label}
      </label>
      <span className="app-choice">
        <input
          id={id}
          type="checkbox"
          title={hint}
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
        />
      </span>
    </div>
  )
}
