import { useHealthReady } from "@/api/health"
import { QueryErrorPanel } from "@/components/shared/QueryErrorPanel"
import { Card, CardBody, PageHeader } from "@/components/ui/Layout"
import { Tag } from "@/components/ui/Tag"

/**
 * 홈 — backend·DB·파일 저장소 연결을 실제로 확인한다(설치 점검, local-setup 「동작 확인」).
 * 조회·로딩·오류 처리의 참고 구현이기도 하다(fetchJson → useQuery → 오류는 QueryErrorPanel). 첫 기능을 만들면 이 화면을 그 프로젝트의 홈으로 바꾼다.
 */
export default function HomePage() {
  const ready = useHealthReady()

  return (
    <section>
      <PageHeader title="홈" description="서버·데이터베이스·파일 저장소 연결을 확인합니다" />
      {ready.isPending && <div className="app-skeleton" aria-busy="true" aria-label="상태 확인 중" />}
      {ready.isError && <QueryErrorPanel error={ready.error} title="서버 상태를 확인하지 못했습니다" />}
      {ready.isSuccess && (
        <Card title={null} note={null} actions={null}>
          <CardBody>
            <div className="flex items-center gap-2">
              <Tag tone="ok">정상</Tag>
              <span>서버·데이터베이스·파일 저장소에 연결되어 있습니다</span>
            </div>
          </CardBody>
        </Card>
      )}
    </section>
  )
}
