import { apiErrorMessage } from "@/api/error-messages"
import { ApiError } from "@/api/transport"

/**
 * 조회 실패의 공용 표시. 빈 목록이나 0 으로 대신 그리지 않는다(기조 1).
 * 요청 ID 를 함께 보여 문의할 때 서버 로그와 맞춰 볼 수 있게 한다.
 */
/** `title` 예: 「항목 목록을 불러오지 못했습니다」 */
export function QueryErrorPanel({ error, title }: { error: unknown; title: string }) {
  const requestId = error instanceof ApiError ? error.diagnostic?.requestId : undefined
  const reason = apiErrorMessage(error)
  return (
    <div className="app-note app-note--danger" role="alert">
      <strong>{title}</strong>
      <p>{reason}</p>
      {requestId && <p className="app-mono">요청 ID {requestId}</p>}
    </div>
  )
}
