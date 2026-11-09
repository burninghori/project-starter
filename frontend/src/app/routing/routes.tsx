import { lazy, Suspense } from "react"
import type { RouteObject } from "react-router"

import { LOGIN_DESCRIPTION } from "@/app/brand"
import { ComingSoonPage } from "@/app/pages/coming-soon/ComingSoonPage"
import { NotFoundPage } from "@/app/pages/not-found/NotFoundPage"
import { AppShell } from "@/app/shell/AppShell"
import { StandaloneLayout } from "@/app/shell/StandaloneLayout"

import { RequireLogin, RequirePasswordChanged } from "./guards"
import { PAGES, type PageConfig } from "./pages-config"
import { RouteErrorBoundary } from "./RouteErrorBoundary"

const LoginPage = lazy(() => import("@/app/pages/auth/LoginPage"))
const PasswordChangePage = lazy(() => import("@/app/pages/auth/PasswordChangePage"))

function PageLoading() {
  return <div className="app-skeleton" aria-busy="true" aria-label="화면을 불러오는 중" />
}

/** 화면이 있으면 그 화면을, 아직 없는 메뉴면 「준비 중」 화면을 그린다(결정 0003) */
function pageElement(page: PageConfig) {
  if (page.status === "coming-soon") {
    return <ComingSoonPage title={page.label} summary={page.summary} />
  }
  const { Component } = page
  return (
    <Suspense fallback={<PageLoading />}>
      <Component />
    </Suspense>
  )
}

/**
 * 라우트 트리. 로그인·비밀번호 변경은 셸 밖(`StandaloneLayout`)이고, 나머지 화면은
 * 로그인(`RequireLogin`) → 비밀번호 변경 게이트(`RequirePasswordChanged`) → 셸 안이다. 화면 오류는 셸 안의 경계가 받는다.
 * `router.tsx` 가 브라우저 라우터로, 테스트(`test/render.tsx` 의 `renderApp`)가 메모리 라우터로 같은 트리를 쓴다.
 */
export const routes: RouteObject[] = [
  {
    path: "/login",
    errorElement: <RouteErrorBoundary />,
    element: (
      <StandaloneLayout description={LOGIN_DESCRIPTION}>
        <Suspense fallback={<PageLoading />}>
          <LoginPage />
        </Suspense>
      </StandaloneLayout>
    ),
  },
  {
    element: <RequireLogin />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        path: "/password",
        element: (
          <StandaloneLayout description={null}>
            <Suspense fallback={<PageLoading />}>
              <PasswordChangePage />
            </Suspense>
          </StandaloneLayout>
        ),
      },
      {
        element: <RequirePasswordChanged />,
        children: [
          {
            element: <AppShell />,
            children: [
              {
                errorElement: <RouteErrorBoundary />,
                children: [
                  ...PAGES.map((page) => ({ path: page.path, element: pageElement(page) })),
                  { path: "*", element: <NotFoundPage /> },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
]
