import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react"

import { cn } from "@/lib/cn"

import { Button, type ButtonSize, type ButtonVariant } from "./Button"

export interface MenuItem {
  /** 보이는 글자 = 접근성 이름. 한 메뉴 안에서 유일하다(React key 로도 쓴다) */
  label: string
  onSelect: () => void
}

interface MenuButtonProps {
  /** 트리거 버튼의 글자 — 트리거와 메뉴의 접근성 이름이 된다(「관리자 · admin」) */
  label: string
  variant: ButtonVariant
  size: ButtonSize
  /** 메뉴를 트리거의 왼쪽 끝(`start`) 또는 오른쪽 끝(`end`)에 맞춘다 — 상단 바처럼 화면 오른쪽에 있으면 end */
  align: "start" | "end"
  /** 빈 메뉴는 타입에서 막는다 */
  items: readonly [MenuItem, ...MenuItem[]]
}

/** 열려 있을 때 어느 항목에 포커스를 둘지. null 이면 닫힘 */
type OpenFocus = "first" | "last"

/**
 * 팝오버 메뉴 — 버튼 하나에 딸린 동작 목록(app-ui-spec 5절 「조작」, app-shell-spec 6절 「떠 있는 면」). WAI-ARIA 「Menu Button」 패턴.
 * - 열기: 클릭(첫 항목 포커스) · ↓(첫 항목) · ↑(마지막 항목). 이동: ↓↑ 순환, Home·End. 선택: 항목 클릭·Enter·Space.
 * - 닫기: 항목 선택 · Esc · Tab · 바깥 클릭 · 트리거 재클릭. 닫히면 포커스는 트리거로 돌아간다(Tab 은 브라우저가 다음 요소로 옮긴다).
 * - 메뉴는 열릴 때만 그린다(닫힘 = DOM 에 없음). 여는 움직임은 없다 — 사용자 조작의 즉각 응답이다.
 * - `onBlur` 로 닫지 않는다: Safari 는 버튼 클릭에 포커스를 주지 않아 항목의 click 이 오기 전에 blur 가 먼저 오고, 그러면 onSelect 가 영영 불리지 않는다.
 * - 상태는 부품 안에 있다(`overlay-store` 와 무관). 트리거가 놓인 면 안에 absolute 로 뜨므로 `overflow` 가 잘리는 조상 안에서는 쓰지 않는다.
 */
export function MenuButton({ label, variant, size, align, items }: MenuButtonProps) {
  const id = useId()
  const triggerId = `${id}-trigger`
  const menuId = `${id}-menu`
  const [openFocus, setOpenFocus] = useState<OpenFocus | null>(null)
  const open = openFocus !== null
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([])

  // 항목은 열릴 때만 그리므로, 그려진 뒤에 포커스를 옮긴다
  useEffect(() => {
    if (openFocus === null) return
    itemRefs.current.at(openFocus === "first" ? 0 : -1)?.focus()
  }, [openFocus])

  // 바깥 mousedown 으로 닫는다 — 열려 있는 동안만 건다. 연 클릭은 리스너가 붙기 전에 끝나 잡히지 않는다
  useEffect(() => {
    if (!open) return
    function onMouseDown(event: MouseEvent) {
      if (event.target instanceof Node && !rootRef.current?.contains(event.target)) setOpenFocus(null)
    }
    document.addEventListener("mousedown", onMouseDown)
    return () => document.removeEventListener("mousedown", onMouseDown)
  }, [open])

  function close() {
    setOpenFocus(null)
    triggerRef.current?.focus()
  }

  function onTriggerKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return
    event.preventDefault()
    setOpenFocus(event.key === "ArrowDown" ? "first" : "last")
  }

  function onMenuKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const count = items.length
    const current = itemRefs.current.findIndex((element) => element === document.activeElement)
    let next: number
    switch (event.key) {
      case "ArrowDown":
        next = current === -1 ? 0 : (current + 1) % count
        break
      case "ArrowUp":
        next = current === -1 ? count - 1 : (current - 1 + count) % count
        break
      case "Home":
        next = 0
        break
      case "End":
        next = count - 1
        break
      case "Escape":
        // 모달 안에서 열렸으면 메뉴만 닫는다 — 모달은 window 의 keydown 으로 닫히므로 거기까지 가지 않게 막는다
        event.stopPropagation()
        close()
        return
      case "Tab":
        // 기본 동작은 막지 않는다 — 닫힌 뒤 브라우저가 트리거의 다음(이전) 요소로 포커스를 옮긴다
        close()
        return
      default:
        return
    }
    event.preventDefault()
    itemRefs.current[next]?.focus()
  }

  return (
    <div ref={rootRef} className="relative inline-flex">
      <Button
        ref={triggerRef}
        id={triggerId}
        variant={variant}
        size={size}
        aria-haspopup="menu"
        aria-expanded={open}
        // 닫혀 있을 때 DOM 에 없는 id 를 가리키지 않는다
        aria-controls={open ? menuId : undefined}
        onClick={() => (open ? close() : setOpenFocus("first"))}
        onKeyDown={onTriggerKeyDown}
      >
        {label}
      </Button>
      {open && (
        <div
          id={menuId}
          role="menu"
          aria-labelledby={triggerId}
          tabIndex={-1}
          className={cn("app-menu", align === "end" && "app-menu--end")}
          onKeyDown={onMenuKeyDown}
        >
          {items.map((item, index) => (
            <button
              key={item.label}
              ref={(element) => {
                itemRefs.current[index] = element
              }}
              type="button"
              role="menuitem"
              tabIndex={-1}
              className="app-menu__item"
              onClick={() => {
                close()
                item.onSelect()
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
