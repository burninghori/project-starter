import { Search } from "lucide-react"
import { useEffect, useRef, useState, type ReactNode, type SelectHTMLAttributes } from "react"

import { cn } from "@/lib/cn"

/**
 * 표 바로 위의 필터 줄 — 「건수 · 셀렉트 · 검색 · 보기 도구 · 빈칸 · 동작 버튼」 한 가지 순서로 그린다(app-ui-spec 5절 「목록 도구」).
 * 검색은 다른 조건과 함께 걸리므로 늘 셀렉트 바로 뒤에 두고, 오른쪽 끝에는 동작 버튼만 붙인다 — 없으면 비운다.
 * 필터를 걸면 바로 옆 건수에서 결과가 보이게 건수를 맨 앞에 고정한다. 동작 버튼 · 보기 도구가 없는 화면은 `null` 로 명시한다.
 *
 * 셀렉트는 모든 화면에서 이 줄에 펼친다 — 단추로 여는 줄에 숨기면 무엇이 걸렸는지 열어 봐야 안다. 좁으면 줄바꿈된다.
 */
export function FilterBar({
  count,
  search,
  tools,
  actions,
  children,
}: {
  count: ReactNode
  search: ReactNode
  /** 검색 바로 뒤의 보기 도구 — 거르지 않고 보이는 모양만 바꾸는 단추(예: 「모두 펼치기」). 없으면 null */
  tools: ReactNode
  /** 오른쪽 끝의 동작 버튼(「항목 추가」 등). 목록 화면은 보통 없다 */
  actions: ReactNode
  /** 조건 입력(`FilterSelect` · 기간 입력 등) — 건수 바로 뒤, 검색 앞 */
  children: ReactNode
}) {
  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      {count}
      {children}
      {search}
      {tools}
      {actions !== null && (
        <>
          <span className="flex-1" />
          <div className="flex items-center gap-2">{actions}</div>
        </>
      )}
    </div>
  )
}

/** 「전체 565건」, 필터가 걸리면 「565건 중 148건」 */
export function FilterCount({ total, shown }: { total: number; shown: number }) {
  return (
    <span className="app-filter-count app-num">
      {shown === total ? (
        <>
          전체 <b>{total.toLocaleString()}</b>건
        </>
      ) : (
        <>
          {total.toLocaleString()}건 중 <b>{shown.toLocaleString()}</b>건
        </>
      )}
    </span>
  )
}

/** 필터 셀렉트(최소 폭 140px). 첫 선택지는 「<이름> · 전체」로 둔다 */
export function FilterSelect({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { "aria-label": string }) {
  return <select className={cn("app-input app-filter-select", className)} {...props} />
}

/** 자동완성식 검색이 입력이 멈춘 뒤 조건을 거는 시간 — 글자마다 다시 그리지 않을 만큼, 기다린다고 느끼지 않을 만큼 */
const FILTER_SEARCH_DEBOUNCE_MS = 300

/**
 * 쳐 가며 결과를 보는 검색 입력(폭 200px) — 입력이 멈추고 0.3초 뒤에 `onChange` 가 불린다.
 * 검색칸은 모두 `SubmitFilterSearch`(돋보기 · Enter)로 통일했고, 이 부품은 자동완성처럼 쳐 가며 후보를 좁혀 봐야 하는
 * 화면만 쓴다 — 지금은 쓰는 화면이 없다. 칸을 비우면 기다리지 않고 바로 조건을 푼다. 바깥에서 `value` 가 바뀌면 입력칸도 따른다.
 * 쓰려면 먼저 그 화면을 예외로 정해 app-ui-spec 5절 「필터 줄」에 적는다 — 「모든 검색칸은 돋보기 · Enter」 규칙을 피해 가는 길로 쓰지 않는다.
 * 지금은 입력 · 디바운스만 맡는다. 후보 목록 · 키보드 이동 · 서버 요청 취소가 필요하면 그 화면을 만들 때 이 부품을 넓힌다.
 */
export function FilterSearch({
  label,
  value,
  onChange,
}: {
  /** 무엇으로 찾는지 — 자리 표시 글자이자 접근성 이름. 예: 「ID · 이름 검색」 */
  label: string
  /** 지금 걸린 검색어 */
  value: string
  onChange: (value: string) => void
}) {
  const [text, setText] = useState(value)
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    setSeen(value)
    setText(value)
  }
  // 부르는 쪽이 그릴 때마다 새 함수를 넘겨도 기다리던 시간이 처음부터 다시 시작되지 않게 마지막 함수를 따로 든다
  const latest = useRef(onChange)
  useEffect(() => {
    latest.current = onChange
  })
  useEffect(() => {
    if (text === value) return
    const timer = setTimeout(() => latest.current(text), FILTER_SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [text, value])
  return (
    <input
      type="search"
      className="app-input app-filter-search"
      placeholder={label}
      aria-label={label}
      value={text}
      onChange={(event) => {
        const next = event.target.value
        setText(next)
        if (next === "" && value !== "") onChange("")
      }}
    />
  )
}

/**
 * 필터 줄의 검색 입력 — 서버에서 찾든 받아 둔 목록 안에서 거르든 모든 검색칸이 쓴다(app-ui-spec 5절 「필터 줄」).
 * 입력칸 안 오른쪽 돋보기 버튼이나 Enter 로만 조건을 건다(치는 동안에는 바뀌지 않는다).
 * 버튼이 있는 모양으로 「눌러야 찾는다」를 보인다. 쳐 가며 후보를 봐야 하는 자동완성식 화면만 예외로 `FilterSearch` 를 쓴다.
 * 칸을 비우면(지우기 ✕ · Esc · 글자 지움) 그때 바로 조건을 푼다 — 빈 칸인데 예전 검색어로 걸러진 채 남지 않게.
 * 바깥에서 `value` 가 바뀌면(필터 초기화 등) 입력칸도 따른다.
 */
export function SubmitFilterSearch({
  label,
  value,
  onSubmit,
}: {
  /** 무엇으로 찾는지 — 자리 표시 글자이자 접근성 이름 */
  label: string
  /** 지금 조회에 걸린 검색어 */
  value: string
  onSubmit: (value: string) => void
}) {
  const [text, setText] = useState(value)
  const [seen, setSeen] = useState(value)
  if (value !== seen) {
    setSeen(value)
    setText(value)
  }
  return (
    <form
      role="search"
      className="relative inline-flex"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit(text)
      }}
    >
      <input
        type="search"
        className="app-input app-filter-search pr-7"
        placeholder={label}
        aria-label={label}
        value={text}
        onChange={(event) => {
          const next = event.target.value
          setText(next)
          if (next === "" && value !== "") onSubmit("")
        }}
      />
      <button
        type="submit"
        className="app-iconbtn absolute top-1/2 right-1.5 -translate-y-1/2"
        aria-label={`${label} 실행`}
      >
        <Search size={14} aria-hidden />
      </button>
    </form>
  )
}
