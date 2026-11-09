/**
 * 도메인 API 모듈의 기본 형태 — 타입, query key, 호출 함수, 조회 훅을 도메인 폴더 하나에 둔다.
 *
 * 새 도메인은 `src/api/<domain>/index.ts` 를 이 파일처럼 만든다. 파일이 커지면 같은 폴더에서
 * `types.ts`·`client.ts`·`queries.ts` 로 나눈다. 다른 도메인 폴더를 고치지 않고 기능을 추가할 수 있어
 * 두 사람이 기능별로 나눠 작업할 때 충돌이 줄어든다.
 */

import { useQuery } from "@tanstack/react-query"

import { fetchJson } from "@/api/transport"

export interface Health {
  status: string
}

/** query key 는 도메인 이름으로 시작한다. invalidate 범위를 도메인 단위로 잡을 수 있다. */
export const healthKeys = {
  all: ["health"] as const,
  live: () => [...healthKeys.all, "live"] as const,
  ready: () => [...healthKeys.all, "ready"] as const,
}

export const healthApi = {
  live: () => fetchJson<Health>("/api/health"),
  ready: () => fetchJson<Health>("/api/health/ready"),
}

export function useHealthReady() {
  return useQuery({ queryKey: healthKeys.ready(), queryFn: healthApi.ready, retry: false })
}
