import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { APP_NAME, LOGIN_DESCRIPTION } from "@/app/brand"

import { StandaloneLayout } from "./StandaloneLayout"

describe("StandaloneLayout", () => {
  it("로그인 화면은 서비스명 아래 설명 한 줄을 보인다", () => {
    render(<StandaloneLayout description={LOGIN_DESCRIPTION}>폼</StandaloneLayout>)

    expect(screen.getByText(APP_NAME)).toBeInTheDocument()
    expect(screen.getByText(LOGIN_DESCRIPTION)).toBeInTheDocument()
  })

  it("설명이 없는 화면(비밀번호 변경 등)은 서비스명만 보인다", () => {
    render(<StandaloneLayout description={null}>폼</StandaloneLayout>)

    expect(screen.getByText(APP_NAME)).toBeInTheDocument()
    expect(screen.queryByText(LOGIN_DESCRIPTION)).not.toBeInTheDocument()
  })
})
