import { isRouteErrorResponse, useRouteError } from "react-router"

/**
 * 화면 렌더 중 처리되지 않은 오류의 마지막 경계. 셸(사이드바)은 남기고 본문 자리만 바꾼다.
 * 원인은 콘솔에 남긴다 — 화면에는 다시 시도할 수 있는 안내만 보인다.
 */
export function RouteErrorBoundary() {
  const error = useRouteError()
  console.error("[route]", error)
  const detail = isRouteErrorResponse(error)
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : String(error)

  return (
    <div className="app-note app-note--danger" role="alert">
      <strong>화면을 표시하지 못했습니다</strong>
      <p>새로고침한 뒤에도 같으면 아래 내용을 함께 알려 주세요</p>
      <p className="app-mono">{detail}</p>
    </div>
  )
}
