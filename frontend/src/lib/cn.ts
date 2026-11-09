import { clsx, type ClassValue } from "clsx"

/** className 조합. 조건부 클래스를 `cn("app-btn", primary && "app-btn--primary")` 처럼 쓴다. */
export function cn(...values: ClassValue[]): string {
  return clsx(values)
}
