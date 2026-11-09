import { MutationCache, QueryClient } from "@tanstack/react-query"

import { apiErrorMessage } from "@/api/error-messages"
import { ApiError } from "@/api/transport"
import { toast } from "@/lib/toast-store"

/**
 * mutation 실패의 공용 토스트. 제목은 「<동작>에 실패했습니다」다.
 *
 * `action` 은 생략할 수 없다 — 생략을 허용하면 무엇이 실패했는지 모르는 토스트가 기본값이 된다(기조 5).
 * 4xx 는 사용자가 입력을 고쳐 넘어설 수 있어 warn, 5xx·네트워크 실패는 danger 다.
 */
export function toastMutationFailure(error: unknown, action: string): void {
  const title = `${action}에 실패했습니다`
  if (error instanceof ApiError) {
    toast(title, error.status >= 500 ? "danger" : "warn", {
      reason: apiErrorMessage(error),
      ...(error.diagnostic ? { requestId: error.diagnostic.requestId } : {}),
    })
    return
  }
  toast(title, "danger", { reason: apiErrorMessage(error) })
}

/**
 * 앱 전체가 쓰는 QueryClient 하나. React 밖(zustand 액션 등)에서도 invalidate 할 수 있게 모듈 싱글턴으로 둔다.
 */
export const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // 자기 onError 를 가진 mutation 은 그쪽이 사용자 안내를 소유한다
      if (mutation.options.onError) return
      console.error("[mutation]", mutation.options.mutationKey, error)
      toastMutationFailure(error, "요청")
    },
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // 4xx 는 다시 해도 결과가 같다. 5xx·네트워크 오류만 한 번 더 시도한다.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status >= 400 && error.status < 500) && failureCount < 1,
      refetchOnWindowFocus: false,
    },
  },
})
