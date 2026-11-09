import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react"

import { cn } from "@/lib/cn"

export type ButtonVariant = "primary" | "secondary" | "danger"
export type ButtonSize = "md" | "sm"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant: ButtonVariant
  size: ButtonSize
}

/**
 * 버튼 하나의 모양 규칙(app-ui-spec 5절 「조작」). `variant`·`size` 는 필수다 — 기본값으로 숨기지 않는다(기조 5).
 * primary 는 한 영역에 하나만 둔다(design-concept 5절).
 * ref 를 넘긴다 — 메뉴 버튼처럼 닫힐 때 포커스를 되돌려야 하는 부품이 쓴다.
 */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant, size, className, type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "app-btn",
        variant !== "secondary" && `app-btn--${variant}`,
        size === "sm" && "app-btn--sm",
        className,
      )}
      {...props}
    />
  )
})

/** 아이콘만 있는 버튼(닫기 ✕ · 빼기 등). 보이는 글자가 없으니 `label` 이 접근성 이름이다 */
export function IconButton({
  label,
  icon,
  onClick,
}: {
  label: string
  icon: ReactNode
  onClick: () => void
}) {
  return (
    <button type="button" className="app-iconbtn" aria-label={label} onClick={onClick}>
      {icon}
    </button>
  )
}
