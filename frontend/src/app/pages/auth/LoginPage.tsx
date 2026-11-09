import { LoaderCircle, LogIn } from "lucide-react"
import { useState, type FormEvent } from "react"
import { Navigate, useLocation } from "react-router"

import { useLogin, useMe, type AuthUser } from "@/api/auth"
import { formFailure } from "@/api/error-messages"
import { Button } from "@/components/ui/Button"
import { Field, FormError, TextInput } from "@/components/ui/Field"
import { PasswordInput } from "@/components/ui/PasswordInput"

/** `RequireLogin` 이 location state 에 남긴 돌아올 경로. 형식이 다르면 없는 것으로 본다(외부 입력) */
function readReturnTo(state: unknown): string | null {
  if (typeof state !== "object" || state === null) return null
  const value = (state as { returnTo?: unknown }).returnTo
  return typeof value === "string" && value.startsWith("/") ? value : null
}

/**
 * 로그인 뒤 갈 곳 — 비밀번호를 바꿔야 하면 그 화면, 아니면 돌아올 경로, 없으면 서버가 준 기본 화면(`defaultPage`) 그대로.
 * 등록되지 않은 경로를 다른 곳으로 대체하지 않는다 — 없는 경로면 「페이지를 찾을 수 없습니다」가 보인다(기조 5)
 */
export function destinationAfterLogin(user: AuthUser, returnTo: string | null): string {
  if (user.mustChangePassword) return "/password"
  return returnTo ?? user.defaultPage
}

type LoginField = "loginId" | "password"

const EMPTY_FIELD_MESSAGES: Record<LoginField, string> = {
  loginId: "아이디를 입력하세요",
  password: "비밀번호를 입력하세요",
}

const NOTHING_MISSING: Record<LoginField, boolean> = { loginId: false, password: false }

function inputOf(form: HTMLFormElement, name: LoginField): HTMLInputElement {
  const field = form.elements.namedItem(name)
  if (!(field instanceof HTMLInputElement)) throw new Error(`로그인 폼에 ${name} 입력이 없다`)
  return field
}

/**
 * 로그인 — 아이디 · 비밀번호 · 「로그인」. 회원가입·비밀번호 찾기 링크 없음(계정은 관리자가 만든다).
 * 무슨 화면인지는 브랜드와 「로그인」 버튼으로 충분해 보이는 제목을 두지 않는다(화면 낭독기용 제목만).
 *
 * 브라우저에 저장한 아이디 · 비밀번호로 「로그인」 한 번에 들어가게 한다. 브라우저 자동 채우기는 입력 이벤트 없이 칸에 값을 넣고,
 * Chrome 은 사용자가 화면을 누르기 전까지 그 값을 화면 코드에 넘기지 않는다 — 그래서
 * - 두 칸은 값을 화면 상태로 들지 않고(비제어), 제출할 때 칸의 실제 값을 읽는다. 상태로 들면 채워진 값을 빈 값으로 덮어쓸 수 있다.
 * - 「로그인」은 처리 중에만 끈다. 빈 칸으로 끄면 첫 클릭이 꺼진 버튼에 닿아 두 번 눌러야 한다.
 *   빈 칸이면 요청하지 않고 그 칸 아래에 안내하고 첫 빈 칸에 커서를 둔다(그 칸을 고치기 시작하면 지운다).
 * 로그인 실패는 버튼 바로 위 빨간 글자 한 줄(토스트·상자 아님)이고, 비밀번호만 비워 다시 입력하게 한다.
 * 이미 로그인돼 있으면 바로 이동한다.
 */
export default function LoginPage() {
  const me = useMe()
  const login = useLogin()
  const location = useLocation()
  const returnTo = readReturnTo(location.state)
  const [missing, setMissing] = useState(NOTHING_MISSING)

  if (me.isPending) {
    return <div className="app-skeleton" aria-busy="true" aria-label="로그인 상태를 확인하는 중" />
  }
  // 로그인 성공도 `me` 캐시가 바뀌어 이 분기로 이동한다
  if (me.data) {
    return <Navigate to={destinationAfterLogin(me.data, returnTo)} replace />
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const loginId = inputOf(form, "loginId").value
    const password = inputOf(form, "password").value
    const nowMissing = { loginId: loginId.length === 0, password: password.length === 0 }
    setMissing(nowMissing)
    if (nowMissing.loginId || nowMissing.password) {
      // 앞선 로그인 실패 문구는 지난 시도의 것이라 내린다
      login.reset()
      inputOf(form, nowMissing.loginId ? "loginId" : "password").focus()
      return
    }
    login.mutate(
      { loginId, password },
      {
        onError: () => {
          // 아이디는 남기고 비밀번호만 비워 바로 다시 입력하게 한다
          const field = inputOf(form, "password")
          field.value = ""
          field.focus()
        },
      },
    )
  }

  function clearMissing(name: LoginField) {
    if (missing[name]) setMissing((current) => ({ ...current, [name]: false }))
  }

  const failure = login.isError ? formFailure(login.error) : null

  return (
    <>
      <h1 className="sr-only">로그인</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
        <Field
          label="아이디"
          required={false}
          labelNote={null}
          hint={null}
          error={missing.loginId ? EMPTY_FIELD_MESSAGES.loginId : null}
        >
          {(control) => (
            <TextInput
              {...control}
              name="loginId"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              onChange={() => clearMissing("loginId")}
            />
          )}
        </Field>
        <Field
          label="비밀번호"
          required={false}
          labelNote={null}
          hint={null}
          error={missing.password ? EMPTY_FIELD_MESSAGES.password : null}
        >
          {(control) => (
            <PasswordInput
              {...control}
              fieldLabel="비밀번호"
              name="password"
              autoComplete="current-password"
              onChange={() => clearMissing("password")}
            />
          )}
        </Field>
        {failure !== null && <FormError requestId={failure.requestId}>{failure.message}</FormError>}
        <Button
          type="submit"
          variant="primary"
          size="md"
          className="mt-1"
          aria-busy={login.isPending}
          disabled={login.isPending}
        >
          {login.isPending ? (
            <LoaderCircle size={16} className="animate-spin" aria-hidden />
          ) : (
            <LogIn size={16} aria-hidden />
          )}
          로그인
        </Button>
      </form>
      <p className="app-note-inline text-center">비밀번호를 잊었다면 관리자에게 문의하세요</p>
    </>
  )
}
