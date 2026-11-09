import { useRef, type KeyboardEvent, type ReactNode } from "react"

import { cn } from "@/lib/cn"

export interface TabItem<T extends string> {
  value: T
  label: ReactNode
}

interface TabsProps<T extends string> {
  /** 탭 묶음의 접근성 이름 */
  label: string
  items: readonly TabItem<T>[]
  value: T
  onChange: (value: T) => void
  /** `main` 은 알약(선택 시 청록 채움), `sub` 는 보조 탭(선택 시 연청록) */
  variant: "main" | "sub"
}

/**
 * 같은 대상의 다른 보기를 바꾸는 탭. 탭 패널은 부르는 쪽이 그린다.
 * 키보드: ←·→ 로 옆 탭으로 옮기며 바로 고른다. 선택된 탭만 Tab 순서에 들어간다.
 */
export function Tabs<T extends string>({ label, items, value, onChange, variant }: TabsProps<T>) {
  const refs = useRef<(HTMLButtonElement | null)[]>([])

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0
    if (step === 0) return
    event.preventDefault()
    const next = (index + step + items.length) % items.length
    const item = items[next]
    if (!item) return
    onChange(item.value)
    refs.current[next]?.focus()
  }

  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-1.5">
      {items.map((item, index) => {
        const selected = item.value === value
        return (
          <button
            key={item.value}
            ref={(element) => {
              refs.current[index] = element
            }}
            type="button"
            role="tab"
            aria-selected={selected}
            tabIndex={selected ? 0 : -1}
            className={cn("app-tab", variant === "sub" && "app-tab--sub")}
            onClick={() => onChange(item.value)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {item.label}
          </button>
        )
      })}
    </div>
  )
}
