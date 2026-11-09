import { cn } from "@/lib/cn"

interface ProgressBarProps {
  /** 0~100. 범위를 벗어나면 막대만 잘라 그린다 — 값 자체는 옆에 숫자로 보인다 */
  value: number
  /** 채움 색 — 높음 ok(청록) · 중간 warn(호박) · 낮음 danger(적). 기준 값은 화면이 정한다 */
  tone: "ok" | "warn" | "danger"
  size: "default" | "mini"
  /** 접근성 이름 — 예: 「진행률」 */
  label: string
}

/** 비율·진행률 막대. 0% 도 보이게 최소 2% 는 그린다 */
export function ProgressBar({ value, tone, size, label }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value))
  const width = Math.max(2, clamped)
  return (
    <div
      className={cn("app-progress", size === "mini" && "app-progress--mini")}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
    >
      {/* 폭은 값에서 계산된다 — 인라인 style 대신 0~100 좌표의 SVG 사각형 폭으로 그린다 */}
      <svg className="block h-full w-full" viewBox="0 0 100 1" preserveAspectRatio="none" aria-hidden>
        <rect
          className={cn("app-progress__fill", tone !== "ok" && `app-progress__fill--${tone}`)}
          width={width}
          height={1}
        />
      </svg>
    </div>
  )
}
