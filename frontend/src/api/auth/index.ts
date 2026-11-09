/**
 * 인증 API 모듈 — 로그인 상태(`/auth/me`)는 TanStack Query 가 소유한다(query key `["auth","me"]`).
 *
 * 로그인 안 됨(401)은 오류가 아니라 상태다: `useMe` 는 그때 `null` 을 준다. 그 밖의 실패(서버 다운 등)는 오류로 올라간다.
 * 비밀번호 규칙은 `./password-rules` 에 있다(backend 와 같은 값).
 */

import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"

import { ApiError, fetchJson } from "@/api/transport"

export interface AuthUser {
  id: number
  loginId: string
  name: string
  /** 역할 값 목록은 미정 — 확정 전엔 코드 값 그대로 보인다 */
  role: string
  mustChangePassword: boolean
  /** 로그인 직후 화면의 경로(새 계정은 `/`). 화면은 이 경로로 그대로 간다 — 등록되지 않은 경로를 대체하지 않는다(기조 5) */
  defaultPage: string
}

interface AuthUserEnvelope {
  user: AuthUser
}

export interface LoginInput {
  loginId: string
  password: string
}

export interface PasswordChangeInput {
  currentPassword: string
  newPassword: string
}

export const authKeys = {
  all: ["auth"] as const,
  me: () => [...authKeys.all, "me"] as const,
}

export const authApi = {
  login: (body: LoginInput) => fetchJson<AuthUserEnvelope>("/auth/login", { method: "POST", body }),
  logout: () => fetchJson<void>("/auth/logout", { method: "POST" }),
  me: () => fetchJson<AuthUserEnvelope>("/auth/me"),
  changePassword: (body: PasswordChangeInput) =>
    fetchJson<AuthUserEnvelope>("/auth/password", { method: "POST", body }),
}

/** 현재 로그인 사용자. 로그인 안 됨이면 `null`. 세션이 바뀌는 곳(로그인·로그아웃·비밀번호 변경)이 캐시를 갱신한다 */
export function useMe() {
  return useQuery({
    queryKey: authKeys.me(),
    queryFn: async (): Promise<AuthUser | null> => {
      try {
        return (await authApi.me()).user
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    retry: false,
    staleTime: Infinity,
  })
}

/**
 * 이 브라우저의 세션을 끝낸다 — 로그인 상태를 「없음」으로 바꾸고 이전 사용자의 화면 데이터·요청 기록을 지운다
 * (다음 사용자에게 이전 데이터가 보이지 않게). 로그아웃 · 세션 만료(인증 요청 밖의 401) · 비밀번호 변경 중 세션 회수가 같이 쓴다.
 * `me` 는 지우지 않고 먼저 `null` 로 바꾼다 — `clear()` 로 함께 지우면 그 값을 보고 있는 라우트 가드가 지워진 옛 쿼리에 남아
 * 갱신을 받지 못하고, 로그인 화면으로 가지 않는다.
 */
export function clearSession(queryClient: QueryClient): void {
  queryClient.setQueryData(authKeys.me(), null)
  const me = queryClient.getQueryCache().find({ queryKey: authKeys.me(), exact: true })
  queryClient.removeQueries({ predicate: (query) => query !== me })
  queryClient.getMutationCache().clear()
}

/**
 * 셸 안 화면이 현재 사용자를 읽는 훅 — `RequireLogin` 아래에서만 쓴다. 가드가 로그인 상태를 이미 확인했으므로 사용자가 없으면
 * 호출 위치가 잘못된 것이다: 기본값으로 숨기지 않고 던진다(기조 5). 던진 오류는 라우트 오류 경계가 받는다.
 * 세션이 끝나 `me` 가 null 이 되는 순간에는 가드가 먼저 로그인 화면으로 보내고 자식을 그리지 않으므로 여기까지 오지 않는다.
 */
export function useCurrentUser(): AuthUser {
  const me = useMe()
  if (me.data === undefined || me.data === null) {
    throw new Error("useCurrentUser: 로그인 상태가 확인되지 않았다 — RequireLogin 안에서만 쓴다")
  }
  return me.data
}

export function useLogin() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: ({ user }) => queryClient.setQueryData(authKeys.me(), user),
    // 로그인 화면이 「로그인」 버튼 바로 위에 한 줄로 보인다 — 공용 토스트(「요청에 실패했습니다」)를 띄우지 않는다
    onError: () => {},
  })
}

/** 로그아웃 — 서버 응답과 무관하게 이 브라우저의 세션을 끝낸다(`clearSession`) */
export function useLogout() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => clearSession(queryClient),
    // 세션이 이미 끝나 401 이 와도 로그아웃은 끝난 것이다 — 토스트를 띄우지 않는다
    onError: () => {},
  })
}

export function useChangePassword() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: authApi.changePassword,
    onSuccess: ({ user }) => queryClient.setQueryData(authKeys.me(), user),
    onError: (error) => {
      // 세션이 끝났으면(관리자 초기화·회수) 세션을 정리해 라우트 가드가 로그인 화면으로 보내게 한다.
      // `/auth/*` 의 401 은 전송 계층이 처리하지 않으므로 여기서 정리한다
      if (
        error instanceof ApiError &&
        (error.code === "auth_required" || error.code === "auth_token_version_stale")
      ) {
        clearSession(queryClient)
      }
      // 그 밖의 오류는 비밀번호 변경 화면이 원인이 있는 칸 아래(어느 칸의 문제도 아니면 버튼 바로 위)에 보인다 — 공용 토스트를 띄우지 않는다
    },
  })
}
