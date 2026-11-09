import type { ReactNode } from "react"
import { create } from "zustand"

/**
 * 떠 있는 면(모달)의 스택. 화면은 `openModal` 로 열고 `OverlayHost` 가 그린다.
 * 같은 모달을 화면마다 따로 마운트하지 않는다 — 열기·닫기·겹침 순서를 이 스택 하나가 정한다.
 */

/** 모달 폭 — default 720px, wide 980px(표가 많은 모달). app-shell-spec 6절 */
export type ModalSize = "default" | "wide"

export interface ModalEntry {
  id: number
  title: string
  size: ModalSize
  /** 모달 내용. `ModalBody`(스크롤되는 본문)와 `ModalFooter`(고정 바닥)를 조합해 돌려준다 */
  render: (close: () => void) => ReactNode
}

interface OverlayState {
  stack: ModalEntry[]
  open: (entry: Omit<ModalEntry, "id">) => number
  close: (id: number) => void
}

let nextId = 1

export const useOverlayStore = create<OverlayState>((set, get) => ({
  stack: [],
  open: (entry) => {
    const id = nextId++
    set({ stack: [...get().stack, { ...entry, id }] })
    return id
  },
  close: (id) => set({ stack: get().stack.filter((entry) => entry.id !== id) }),
}))

export function openModal(entry: Omit<ModalEntry, "id">): number {
  return useOverlayStore.getState().open(entry)
}
