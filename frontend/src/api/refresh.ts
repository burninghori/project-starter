/**
 * 쓰기 뒤 다시 읽을 캐시를 한곳에서 정한다. 쓰기 훅은 「무엇이 바뀌었나」(`ServerChange`)만 말하고, 어느 메뉴의 조회를 다시 읽을지는
 * 아래 표가 정한다 — 한 메뉴의 쓰기가 다른 메뉴가 읽어 둔 값(목록의 건수 · 이름 등)을 바꾸면 그 메뉴의 캐시도 표에 적는다.
 * 빠뜨리면 그 메뉴는 캐시를 다시 읽지 않는 동안(`staleTime`) 옛 값을 지금 값처럼 보인다(기조 1).
 *
 * 표는 각 메뉴의 `keys.ts` 만 import 한다 — 쓰기 훅이 있는 `index.ts` 가 이 파일을 import 하므로 서로 import 하지 않게.
 *
 * 아직 쓰기 기능이 없어 바뀜 종류가 없다(`never`). 첫 쓰기 기능이 `ServerChange` 를 문자열 union 으로 바꾸고 `REFRESH` 에 줄을 더한다
 * — `Record<ServerChange, …>` 라 줄이 빠지면 컴파일이 실패한다.
 */

import type { QueryClient, QueryKey } from "@tanstack/react-query"

/** 바뀐 서버 데이터의 종류 — 예: `"item"`(항목 추가 · 수정 · 삭제) */
export type ServerChange = never

/** 바뀐 것 → 다시 읽을 캐시(메뉴 단위). 화면에 떠 있는 조회는 바로 다시 읽고, 나머지는 「낡음」 표시만 되어 다음에 열 때 읽는다 */
const REFRESH: Record<ServerChange, readonly QueryKey[]> = {}

/** `change` 로 바뀌는 캐시를 모두 무효로 한다 — 떠 있는 조회를 다시 읽기까지 끝나면 끝난다 */
export async function refreshAfter(queryClient: QueryClient, change: ServerChange): Promise<void> {
  const queryKeys: readonly QueryKey[] = REFRESH[change]
  await Promise.all(queryKeys.map((queryKey) => queryClient.invalidateQueries({ queryKey })))
}
