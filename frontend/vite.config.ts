import { readFileSync } from "node:fs"
import path from "node:path"
import { parseEnv } from "node:util"

import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

/**
 * 개발 서버의 /api 프록시 목적지 — backend 포트(APP_PORT)를 backend/.env 에서 읽는다.
 * 프로세스 env 가 있으면 그 값이 이긴다(pydantic-settings 와 같은 우선순위). 둘 다 없으면 시작하지 않는다.
 */
function backendPort(): string {
  const fromEnv = process.env.APP_PORT
  if (fromEnv !== undefined) return fromEnv
  try {
    const parsed = parseEnv(readFileSync(path.resolve(__dirname, "../backend/.env"), "utf8"))
    if (parsed.APP_PORT) return parsed.APP_PORT
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error
  }
  throw new Error("APP_PORT 가 필요하다 — backend/.env 를 만들거나(.env.example 복사) APP_PORT 를 주입한다")
}

export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
    // React 가 두 벌 로드되면 훅이 깨진다. 의존성이 자기 사본을 끌어와도 하나로 모은다.
    dedupe: ["react", "react-dom"],
  },
  server: {
    port: 5174,
    strictPort: true,
    // 배포에서는 앞단(리버스 프록시 · CDN)이 /api/* 를 backend 로 보낸다. 로컬은 이 프록시가 같은 역할이다.
    proxy: command === "serve" ? { "/api": `http://127.0.0.1:${backendPort()}` } : undefined,
  },
}))
