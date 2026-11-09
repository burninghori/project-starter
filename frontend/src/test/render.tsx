import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import type { ReactNode } from "react"
import { createMemoryRouter, MemoryRouter, RouterProvider, useLocation } from "react-router"

import { routerFlushSync } from "@/app/routing/flush-sync"
import { routes } from "@/app/routing/routes"

function newQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

/**
 * 화면 테스트의 공용 틀 — 테스트마다 새 QueryClient(재시도 없음)와 메모리 라우터.
 * 도메인 API 는 `vi.spyOn(xxxApi, "…")` 로 가로채고 실제 훅·화면을 그린다(HomePage.test 와 같은 방식).
 * 캐시 상태를 확인하려는 테스트를 위해 그 QueryClient 를 함께 돌려준다.
 */
export function renderWithProviders(
  ui: ReactNode,
  { route }: { route: string | { pathname: string; state: unknown } },
) {
  const client = newQueryClient()
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
  return { ...result, client }
}

/**
 * 실제 라우트 트리(`routes`)로 앱을 그린다 — 가드·셸·화면을 함께 확인하는 테스트용.
 * 현재 위치는 `router.state.location` 으로 읽는다. 앱(main.tsx)과 같은 `routerFlushSync` 를 넘겨 `navigate(…, { flushSync })` 도
 * 똑같이 동기 커밋된다.
 */
export function renderApp({ route }: { route: string }) {
  const client = newQueryClient()
  const router = createMemoryRouter(routes, { initialEntries: [route] })
  const result = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} flushSync={routerFlushSync} />
    </QueryClientProvider>,
  )
  return { ...result, client, router }
}

/** 라우팅 결과를 확인하는 자리 — 현재 경로와 location state 를 글자로 보인다 */
export function LocationProbe() {
  const location = useLocation()
  return (
    <>
      <p data-testid="location">{location.pathname}</p>
      <p data-testid="location-state">{JSON.stringify(location.state)}</p>
    </>
  )
}
