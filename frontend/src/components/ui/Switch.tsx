/**
 * 스위치 — 켜고 끄는 한 칸(app-ui-spec 5절 「스위치」). 사용 · 사용 안 함처럼 둘 중 하나인 상태를 바로 바꾼다.
 * 접근성 이름은 무엇을 켜고 끄는지(`label` — 「사용 여부」)로 고정하고, 켜짐은 `aria-checked` 로 알린다. 상태 글자
 * (`onLabel` · `offLabel`)는 눈에 보이는 표시다.
 */
export function Switch({
  label,
  checked,
  disabled,
  onLabel,
  offLabel,
  title,
  onChange,
}: {
  /** 접근성 이름 — 무엇을 켜고 끄는가 */
  label: string
  checked: boolean
  disabled: boolean
  onLabel: string
  offLabel: string
  /** 마우스를 올리면 보이는 안내(누르면 무엇이 되는지). 없으면 null */
  title: string | null
  onChange: (checked: boolean) => void
}) {
  return (
    <button
      type="button"
      role="switch"
      className="app-switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      title={title ?? undefined}
      onClick={() => onChange(!checked)}
    >
      <span className="app-switch__track" aria-hidden />
      {checked ? onLabel : offLabel}
    </button>
  )
}
