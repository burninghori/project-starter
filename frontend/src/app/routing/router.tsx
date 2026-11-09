import { createBrowserRouter } from "react-router"

import { routes } from "./routes"

/** 앱 라우터. 라우트 트리는 `routes.tsx` 에 있다 — 테스트가 같은 트리를 메모리 라우터로 쓴다 */
export const router = createBrowserRouter(routes)
