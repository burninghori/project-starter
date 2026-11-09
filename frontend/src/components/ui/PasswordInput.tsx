import { Eye, EyeOff } from "lucide-react"
import {
  useEffect,
  useId,
  useRef,
  useState,
  type FocusEvent,
  type InputHTMLAttributes,
  type KeyboardEvent,
} from "react"

import { cn } from "@/lib/cn"

import type { FieldControl } from "./Field"

/** 이 부품이 정하는 속성은 받지 않는다 — 부르는 쪽이 덮어쓰면 보기 버튼·Caps Lock 경고·자동 완성이 깨진다 */
type NativeProps = Omit<
  InputHTMLAttributes<HTMLInputElement>,
  | "type"
  | "id"
  | "aria-describedby"
  | "aria-invalid"
  | "aria-required"
  | "autoComplete"
  | "spellCheck"
  | "autoCapitalize"
  | "onKeyDown"
  | "onKeyUp"
>

interface PasswordInputProps extends NativeProps, FieldControl {
  /** 보기 버튼 이름에 쓰는 칸 이름. 한 화면에 칸이 여럿이면 「현재 비밀번호 보기」「새 비밀번호 보기」처럼 달라야 한다 */
  fieldLabel: string
  /** 로그인은 current-password, 새로 정할 때는 new-password — 비밀번호 관리자가 이 값으로 채우거나 제안한다 */
  autoComplete: "current-password" | "new-password"
}

/**
 * 비밀번호 입력(app-ui-spec 5절 「입력」) — `Field` 안에서 `{...control}` 로 펼쳐 쓴다.
 * - 칸 안 오른쪽 보기 버튼으로 입력한 값을 확인한다. 마우스로 눌러도 커서는 입력에 남는다.
 *   폼을 제출하면 다시 가린다 — 보이는 채로 제출된 값을 브라우저가 일반 입력의 자동 완성 후보로 저장하지 않게 한다.
 * - Caps Lock 이 켜진 채 입력하면 칸 아래에 경고를 보인다(켜졌을 때만, 칸을 떠나면 숨긴다).
 * - 붙여넣기·자동 완성을 막지 않는다 — 비밀번호 관리자가 동작해야 한다(WCAG 2.2 3.3.8).
 */
export function PasswordInput({
  fieldLabel,
  autoComplete,
  id,
  "aria-describedby": describedBy,
  "aria-invalid": invalid,
  className,
  onBlur,
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const capsLockId = useId()

  useEffect(() => {
    const form = inputRef.current?.form
    if (!form) return
    const hide = () => setVisible(false)
    form.addEventListener("submit", hide)
    return () => form.removeEventListener("submit", hide)
  }, [])

  function trackCapsLock(event: KeyboardEvent<HTMLInputElement>) {
    setCapsLock(event.getModifierState("CapsLock"))
  }

  function handleBlur(event: FocusEvent<HTMLInputElement>) {
    setCapsLock(false)
    onBlur?.(event)
  }

  const describedByWithWarning = [describedBy, capsLock ? capsLockId : undefined]
    .filter((value) => value !== undefined)
    .join(" ")

  return (
    <>
      <div className="relative">
        <input
          {...props}
          ref={inputRef}
          id={id}
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          spellCheck={false}
          autoCapitalize="none"
          aria-describedby={describedByWithWarning === "" ? undefined : describedByWithWarning}
          aria-invalid={invalid}
          className={cn("app-input w-full pr-10", className)}
          onKeyDown={trackCapsLock}
          onKeyUp={trackCapsLock}
          onBlur={handleBlur}
        />
        <button
          type="button"
          className="app-password__toggle absolute inset-y-0 right-0 flex items-center px-3"
          aria-label={`${fieldLabel} 보기`}
          aria-controls={id}
          aria-pressed={visible}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? <EyeOff size={16} aria-hidden /> : <Eye size={16} aria-hidden />}
        </button>
      </div>
      {capsLock && (
        <p id={capsLockId} className="app-field__hint app-field__hint--warn">
          Caps Lock 이 켜져 있습니다
        </p>
      )}
    </>
  )
}
