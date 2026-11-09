import { Link } from "react-router"

export function NotFoundPage() {
  return (
    <section className="flex flex-col gap-3">
      <h1 className="app-title">페이지를 찾을 수 없습니다</h1>
      <p>주소를 확인하거나 메뉴에서 화면을 골라 주세요</p>
      <Link to="/" className="app-link">
        첫 화면으로
      </Link>
    </section>
  )
}
