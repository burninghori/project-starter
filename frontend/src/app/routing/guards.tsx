import { useQueryClient } from "@tanstack/react-query"
import { useEffect } from "react"
import { Navigate, Outlet, useLocation } from "react-router"

import { clearSession, useMe } from "@/api/auth"
import { setUnauthorizedHandler } from "@/api/transport"
import { StandaloneLayout } from "@/app/shell/StandaloneLayout"
import { QueryErrorPanel } from "@/components/shared/QueryErrorPanel"

/** 로그인 화면이 돌아갈 곳 — `RequireLogin` 이 location state 로 넘기고 LoginPage 가 읽는다 */
export interface LoginLocationState {
  returnTo: string
}

/**
 * 로그인된 사용자만 지나간다. 아니면 로그인 화면으로 보내고 돌아올 경로를 기억한다.
 * 세션이 중간에 끝나면(인증 요청 밖의 401) 전송 계층이 알려 주고, 같은 길로 로그인 화면에 간다.
 */
export function RequireLogin() {
  const me = useMe()
  const location = useLocation()
  const queryClient = useQueryClient()

  useEffect(() => {
    // 세션을 정리하면(로그인 상태 「없음」 + 이전 화면 데이터 삭제) 아래 분기가 로그인 화면으로 보낸다
    setUnauthorizedHandler(() => clearSession(queryClient))
    return () => setUnauthorizedHandler(null)
  }, [queryClient])

  if (me.isPending) {
    return <div className="app-skeleton" aria-busy="true" aria-label="로그인 상태를 확인하는 중" />
  }
  if (me.isError) {
    return (
      <StandaloneLayout description={null}>
        <QueryErrorPanel error={me.error} title="로그인 상태를 확인하지 못했습니다" />
      </StandaloneLayout>
    )
  }
  if (me.data === null) {
    const state: LoginLocationState = { returnTo: location.pathname + location.search }
    return <Navigate to="/login" replace state={state} />
  }
  return <Outlet />
}

/** 비밀번호를 바꿔야 하는 사용자는 비밀번호 변경 화면 밖으로 갈 수 없다 — `RequireLogin` 아래에서만 쓴다 */
export function RequirePasswordChanged() {
  const me = useMe()
  if (me.data !== undefined && me.data !== null && me.data.mustChangePassword) {
    return <Navigate to="/password" replace />
  }
  return <Outlet />
}
