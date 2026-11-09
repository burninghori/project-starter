import { useState } from "react"

export interface ExpandedRows {
  isOpen: (key: string) => boolean
  toggle: (key: string) => void
  /** 키가 모두 펼쳐져 있는가 — 키가 없으면 false */
  allOpen: (keys: readonly string[]) => boolean
  /** 키가 모두 펼쳐져 있으면 모두 접고, 아니면 모두 펼친다 */
  toggleAll: (keys: readonly string[]) => void
}

interface ExpansionState {
  resetKey: string
  /** 처음 펼칠 줄을 이 조건에서 이미 정했는가 */
  seeded: boolean
  open: ReadonlySet<string>
}

/**
 * 표의 펼친 줄(아코디언) 상태 — 펼친 줄이 있는 표가 같이 쓴다(app-ui-spec 5절 「목록 도구」 「펼친 줄 패널」).
 *
 * - 조건(`resetKey` — 필터 · 검색처럼 목록을 바꾸는 값을 이은 글자)이 바뀌면 펼친 줄을 비운다. 쪽은 조건에 넣지 않는다 — 쪽을 넘겼다 돌아와도 펼친 줄이 남는다.
 * - 처음 펼칠 줄(`initial`)은 그 조건의 데이터가 처음 온 뒤 한 번만 정한다. 데이터가 아직 없으면 `null` 을 넘긴다 —
 *   예: 주소로 가리킨 ID 의 줄, 실패한 줄 전부.
 * - 「모두 펼치기 / 모두 접기」는 넘긴 키(이 쪽의 줄)만 대상이다.
 *
 * 조건이 바뀐 것을 렌더 중에 보고 상태를 맞춘다(React 의 「이전 렌더 값과 비교해 상태 고치기」) — effect 로 맞추면 한 번은 옛 펼침으로 그려진다.
 */
export function useExpandedRows(resetKey: string, initial: readonly string[] | null): ExpandedRows {
  const [state, setState] = useState<ExpansionState>({ resetKey, seeded: false, open: new Set() })

  let current = state
  if (current.resetKey !== resetKey) {
    current = { resetKey, seeded: false, open: new Set() }
  }
  if (!current.seeded && initial !== null) {
    current = { ...current, seeded: true, open: new Set(initial) }
  }
  if (current !== state) setState(current)

  const open = current.open

  function allOpen(keys: readonly string[]): boolean {
    return keys.length > 0 && keys.every((key) => open.has(key))
  }

  return {
    isOpen: (key) => open.has(key),
    toggle: (key) => {
      setState((prev) => {
        const next = new Set(prev.open)
        if (next.has(key)) next.delete(key)
        else next.add(key)
        return { ...prev, open: next }
      })
    },
    allOpen,
    toggleAll: (keys) => {
      const closing = allOpen(keys)
      setState((prev) => {
        const next = new Set(prev.open)
        for (const key of keys) {
          if (closing) next.delete(key)
          else next.add(key)
        }
        return { ...prev, open: next }
      })
    },
  }
}
