import { create } from "zustand"

/**
 * 토스트 알림 상태. Zustand 는 이런 화면 상태(UI 상태)에만 쓴다 — 서버 데이터는 TanStack Query 가 소유한다.
 *
 * tone: info(안내) · success(완료) · warn(사용자가 고칠 수 있는 실패) · danger(사용자가 할 수 없는 실패)
 */
export type ToastTone = "info" | "success" | "warn" | "danger"

export interface Toast {
  id: number
  title: string
  tone: ToastTone
  reason?: string
  /** 문의할 때 쓰는 서버 요청 ID */
  requestId?: string
}

interface ToastState {
  toasts: Toast[]
  push: (toast: Omit<Toast, "id">) => void
  dismiss: (id: number) => void
}

const AUTO_DISMISS_MS = 6000
let nextId = 1

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],
  push: (toast) => {
    const id = nextId++
    set({ toasts: [...get().toasts, { ...toast, id }] })
    window.setTimeout(() => get().dismiss(id), AUTO_DISMISS_MS)
  },
  dismiss: (id) => set({ toasts: get().toasts.filter((toast) => toast.id !== id) }),
}))

export function toast(title: string, tone: ToastTone, extra: Pick<Toast, "reason" | "requestId"> = {}): void {
  useToastStore.getState().push({ title, tone, ...extra })
}
