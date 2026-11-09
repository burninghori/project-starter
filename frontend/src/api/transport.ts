/**
 * backend 호출의 단일 경로 — URL 조립, JSON 직렬화, 오류 envelope 해석을 이 모듈이 소유한다.
 *
 * 화면과 훅은 `fetchJson` 만 쓴다(eslint 가 `fetch` 직접 호출을 막는다). 가짜 응답·fixture 경로를
 * 두지 않는다(기조 1) — 실패는 `ApiError` 로 올라가 화면이 오류 상태로 보여준다.
 */

import { API_ERROR_STATUS, type ApiErrorCode, type ApiErrorFamily } from "./error-codes.generated"

export type { ApiErrorCode, ApiErrorFamily }

/** backend 목록에 없는 code(배포 시차로 backend 가 더 새로운 경우)나 계약 밖 오류 본문 */
export type ApiErrorCodeOrUnknown = ApiErrorCode | "unknown_error"

export type RequestMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE"
export type Query = Record<string, boolean | number | string | string[] | undefined>

export interface ApiErrorDiagnostic {
  requestId: string
  message?: string
}

/** 서버가 응답은 했지만 2xx 가 아닌 경우의 공통 표식. 네트워크 단절(TypeError)과 구분한다. */
export class HttpResponseError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = "HttpResponseError"
  }
}

/**
 * backend 오류 envelope(semantic-v1)을 해석한 오류.
 *
 * `message` 는 `HTTP 404 · resource_not_found` 같은 로컬 표식이다. 사용자 문구는 `apiErrorMessage`
 * (error-messages.ts)가 `code`·`details` 로 만든다. `diagnostic.message` 는 원문이라 주 문구로 쓰지 않는다.
 * `rawCode` 는 응답에 실려 온 code 원문이다 — 목록에 없는 code 도 진단용으로 남긴다.
 */
export class ApiError extends HttpResponseError {
  constructor(
    status: number,
    readonly family: ApiErrorFamily | null,
    readonly code: ApiErrorCodeOrUnknown,
    readonly details: Record<string, unknown> | undefined,
    readonly diagnostic: ApiErrorDiagnostic | null,
    readonly rawCode: string = code,
  ) {
    super(status, `HTTP ${status} · ${rawCode}`)
    this.name = "ApiError"
  }
}

function isKnownCode(code: string): code is ApiErrorCode {
  return Object.hasOwn(API_ERROR_STATUS, code)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

/** 오류 응답 본문을 `ApiError` 로 세운다. 계약에 맞지 않는 본문은 `unknown_error` 로 둔다. */
export function apiErrorFromBody(status: number, body: unknown): ApiError {
  const error = isRecord(body) ? body.error : undefined
  if (!isRecord(error) || error.contract !== "semantic-v1" || typeof error.code !== "string") {
    return new ApiError(status, null, "unknown_error", undefined, null)
  }
  const diagnostic = isRecord(error.diagnostic) ? error.diagnostic : null
  return new ApiError(
    status,
    typeof error.family === "string" ? (error.family as ApiErrorFamily) : null,
    isKnownCode(error.code) ? error.code : "unknown_error",
    isRecord(error.details) ? error.details : undefined,
    diagnostic && typeof diagnostic.requestId === "string"
      ? {
          requestId: diagnostic.requestId,
          ...(typeof diagnostic.message === "string" ? { message: diagnostic.message } : {}),
        }
      : null,
    error.code,
  )
}

/** `/items` → `/api/v1/items`. `/api/` 로 시작하면 그대로 둔다(`/api/health`). */
export function apiPath(path: string, query?: Query): string {
  const pathname = path.startsWith("/api/") ? path : `/api/v1${path.startsWith("/") ? path : `/${path}`}`
  if (!query) return pathname
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined) continue
    if (Array.isArray(value)) {
      for (const item of value) params.append(key, item)
    } else {
      params.set(key, String(value))
    }
  }
  const search = params.toString()
  return search ? `${pathname}?${search}` : pathname
}

export interface FetchOptions {
  method?: RequestMethod
  query?: Query
  /** JSON 으로 직렬화할 본문. FormData 는 그대로 보낸다(파일 업로드). */
  body?: unknown
  signal?: AbortSignal
  /** 페이지가 사라져도(탭 닫기 · 새로고침) 요청을 끝까지 보낸다 — `pagehide` 에서 보내는 정리 요청용. 본문은 64KB 까지 */
  keepalive?: boolean
}

/**
 * 세션 만료 처리(로그인 화면으로 보내기)에서 빠지는 경로 — 로그인 화면·`/auth/*` 요청은 예외다(그 401 은 호출한 화면이 처리한다).
 * 이 경로의 401 은 부른 쪽이 그 자리에서 다룬다(로그인 실패 문구, `useMe` 의 로그인 안 됨 `null` 등)
 */
const AUTH_PATH_PREFIX = "/api/v1/auth/"

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler | null = null

/**
 * 세션 만료(인증 요청 밖의 401)를 받았을 때 부를 콜백. 라우터를 아는 쪽(라우트 가드)이 등록한다 —
 * 전송 계층은 라우터를 모른다. `null` 로 해제한다.
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler
}

export async function fetchJson<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = "GET", query, body, signal, keepalive = false } = options
  const headers: Record<string, string> = { accept: "application/json" }
  let requestBody: BodyInit | undefined
  if (body instanceof FormData) {
    requestBody = body
  } else if (body !== undefined) {
    headers["content-type"] = "application/json"
    requestBody = JSON.stringify(body)
  }

  const url = apiPath(path, query)
  const response = await fetch(url, {
    method,
    headers,
    body: requestBody,
    signal,
    keepalive,
    credentials: "same-origin",
  })

  if (!response.ok) {
    let payload: unknown = null
    try {
      payload = await response.json()
    } catch {
      // JSON 이 아닌 오류 본문(프록시 502 HTML 등)은 계약 밖이다. status 만으로 unknown_error 를 세운다.
    }
    const error = apiErrorFromBody(response.status, payload)
    if (error.status === 401 && !url.startsWith(AUTH_PATH_PREFIX)) onUnauthorized?.()
    throw error
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
