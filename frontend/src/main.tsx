import React from "react"
import ReactDOM from "react-dom/client"
import { RouterProvider } from "react-router"

// 전역 스타일은 이 시트 하나만 import 한다(Tailwind → app 토큰 → app 컴포넌트 순서는 app.css 가 소유)
import "./styles/app/app.css"
import { Providers } from "./app/Providers"
import { routerFlushSync } from "./app/routing/flush-sync"
import { router } from "./app/routing/router"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Providers>
      <RouterProvider router={router} flushSync={routerFlushSync} />
    </Providers>
  </React.StrictMode>,
)
