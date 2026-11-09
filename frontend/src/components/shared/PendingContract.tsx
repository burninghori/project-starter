/**
 * 화면에는 자리가 있는데 아직 채울 backend 계약이 없는 곳의 표시.
 *
 * 값을 지어내거나 자리를 지우지 않는다(기조 1). 무채 점선 칩으로 「백엔드 연동 필요」를 보이고,
 * `need` 에 무엇이 있어야 채워지는지 적는다. 같은 계약은 코드의 `TODO(be)` 와 문구를 맞춘다.
 */
export function PendingContract({ need }: { need: string }) {
  return (
    <span className="app-pending" title={need}>
      백엔드 연동 필요
    </span>
  )
}
