import { PageHeader } from "@/components/ui/Layout"
import { Note } from "@/components/ui/Note"

/**
 * 「준비 중」 화면(결정 0003, app-ui-spec 「메뉴 공개 상태」) — 화면이 아직 없는 메뉴를 누르면 연다. 제목은 메뉴 이름, 설명은 그 화면이 할 일
 * 한 줄(pages-config 의 `summary`)이다. 목업 화면 · 예시 데이터는 보이지 않는다(기조 1).
 */
export function ComingSoonPage({ title, summary }: { title: string; summary: string }) {
  return (
    <section>
      <PageHeader title={title} description={summary} />
      <Note tone="plain">준비 중인 화면입니다</Note>
    </section>
  )
}
