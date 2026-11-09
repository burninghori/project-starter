import { QueryClientProvider } from "@tanstack/react-query"
import { ReactQueryDevtools } from "@tanstack/react-query-devtools"
import type { ReactNode } from "react"

import { queryClient } from "@/lib/query-client"

/** 앱 전역 provider. 라우터 위에 두어 모든 화면이 QueryClient 캐시 하나를 함께 쓴다. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />}
    </QueryClientProvider>
  )
}
