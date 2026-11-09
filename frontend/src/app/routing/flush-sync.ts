import { flushSync } from "react-dom"
import type { RouterProviderProps } from "react-router"

/**
 * `RouterProvider` 에 넘기는 동기 커밋 함수 — `navigate(…, { flushSync: true })` 가 그 자리에서 커밋되게 한다(로그아웃 흐름, app-shell-spec 5절).
 * `react-router/dom` 의 RouterProvider 가 하는 일이 이것뿐인데, 그 진입점을 따로 쓰면 테스트 환경에서 `react-router` 와 다른 빌드로 풀려
 * 라우터 컨텍스트가 두 벌이 된다. 그래서 `react-router` 한 진입점만 쓰고 여기서 직접 넘긴다(main.tsx · test/render.tsx).
 * react-dom 의 `flushSync` 는 값을 돌려주는 제네릭이라 prop 타입(`(fn) => undefined`)에 맞게 감싼다.
 */
export const routerFlushSync: NonNullable<RouterProviderProps["flushSync"]> = (fn) => {
  flushSync(fn)
}
