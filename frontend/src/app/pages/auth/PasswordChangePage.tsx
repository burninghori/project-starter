import { KeyRound, LoaderCircle } from "lucide-react"
import { useState, type FormEvent } from "react"
import { Navigate, useNavigate } from "react-router"

import { useChangePassword, useMe } from "@/api/auth"
import {
  PASSWORD_RULE_MESSAGES,
  PASSWORD_RULE_SUMMARY,
  passwordRuleViolation,
} from "@/api/auth/password-rules"
import { apiErrorMessage, formFailure, type FormFailure } from "@/api/error-messages"
import { ApiError } from "@/api/transport"
import { Button } from "@/components/ui/Button"
import { Field, FormError } from "@/components/ui/Field"
import { PasswordInput } from "@/components/ui/PasswordInput"
import { toast } from "@/lib/toast-store"

const CONFIRM_MISMATCH = "새 비밀번호와 확인이 서로 다릅니다"

/** 칸마다의 오류 한 줄. `form` 은 어느 칸의 문제도 아닌 오류(연결 실패·서버 오류 — 서버 오류면 요청 ID 도). 세션이 끝난 경우는 로그인 화면으로 간다(`useChangePassword`) */
interface ChangeErrors {
  current: string | null
  next: string | null
  form: FormFailure | null
}

const NO_ERRORS: ChangeErrors = { current: null, next: null, form: null }

/** 서버 오류를 원인이 있는 칸으로 보낸다 — 문구는 apiErrorMessage 가 정하고 여기서는 자리만 고른다 */
function placeServerError(error: unknown): ChangeErrors {
  const message = apiErrorMessage(error)
  if (error instanceof ApiError && error.code === "auth_current_password_invalid") {
    return { ...NO_ERRORS, current: message }
  }
  if (error instanceof ApiError && error.code === "auth_password_rule_violation") {
    return { ...NO_ERRORS, next: message }
  }
  return { ...NO_ERRORS, form: formFailure(error) }
}

/**
 * 비밀번호 변경 — 현재 · 새 · 확인. 제출 전에 backend 와 같은 규칙으로 미리 검사하고,
 * 오류는 원인이 있는 칸 바로 아래에 보인다. 새 비밀번호의 규칙은 칸 아래 안내 한 줄로 입력 전부터 보인다
 * (칸 안 placeholder 는 입력을 시작하면 사라져서 쓰지 않는다).
 * 임시 비밀번호로 들어온 사용자는 여기를 지나야 다른 화면을 쓸 수 있다(라우트 가드).
 * 바꾸면 로그인을 유지한 채(결정 0006 — 쿠키 재발급) 기본 화면으로 가고, 거기서 성공 토스트가 보인다.
 */
export default function PasswordChangePage() {
  const me = useMe()
  const change = useChangePassword()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  // 확인 칸은 떠난 뒤(또는 제출한 뒤)부터 일치 여부를 보인다 — 입력하는 도중에 오류를 띄우지 않는다
  const [confirmChecked, setConfirmChecked] = useState(false)
  const [errors, setErrors] = useState<ChangeErrors>(NO_ERRORS)

  if (me.isPending) {
    return <div className="app-skeleton" aria-busy="true" aria-label="로그인 상태를 확인하는 중" />
  }
  if (!me.data) {
    return <Navigate to="/login" replace />
  }
  const user = me.data
  const confirmError =
    confirmChecked && confirmPassword.length > 0 && confirmPassword !== newPassword ? CONFIRM_MISMATCH : null

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setConfirmChecked(true)
    const violation = passwordRuleViolation(newPassword)
    setErrors({ ...NO_ERRORS, next: violation === null ? null : PASSWORD_RULE_MESSAGES[violation] })
    if (violation !== null || newPassword !== confirmPassword) return
    change.mutate(
      { currentPassword, newPassword },
      {
        onSuccess: ({ user: updated }) => {
          // 토스트 상태는 전역 store 라 이동한 셸의 Toaster 가 그린다(셸 밖 화면에는 Toaster 가 없다)
          toast("비밀번호를 바꿨습니다", "success")
          navigate(updated.defaultPage, { replace: true })
        },
        onError: (error) => setErrors(placeServerError(error)),
      },
    )
  }

  return (
    <>
      <div className="flex flex-col gap-1">
        <h1 className="app-standalone__title">비밀번호 변경</h1>
        {user.mustChangePassword && (
          // 한글이 글자 중간에서 줄바꿈되지 않게 띄어쓰기에서만 나눈다
          <p className="app-desc break-keep">
            임시 비밀번호로 로그인했습니다. 새 비밀번호를 정해야 다른 화면을 쓸 수 있습니다
          </p>
        )}
      </div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate>
        {/* 비밀번호 관리자가 어느 계정의 비밀번호를 바꾸는지 알게 한다 — 보이지 않고 조작할 수 없다 */}
        <input
          className="sr-only"
          type="text"
          name="username"
          autoComplete="username"
          value={user.loginId}
          readOnly
          tabIndex={-1}
          aria-hidden
        />
        <Field label="현재 비밀번호" required={false} labelNote={null} hint={null} error={errors.current}>
          {(control) => (
            <PasswordInput
              {...control}
              fieldLabel="현재 비밀번호"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => {
                setCurrentPassword(event.target.value)
                setErrors((current) => ({ ...current, current: null }))
              }}
            />
          )}
        </Field>
        <Field
          label="새 비밀번호"
          required={false}
          labelNote={null}
          hint={PASSWORD_RULE_SUMMARY}
          error={errors.next}
        >
          {(control) => (
            <PasswordInput
              {...control}
              fieldLabel="새 비밀번호"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => {
                setNewPassword(event.target.value)
                setErrors((current) => ({ ...current, next: null }))
              }}
            />
          )}
        </Field>
        <Field label="새 비밀번호 확인" required={false} labelNote={null} hint={null} error={confirmError}>
          {(control) => (
            <PasswordInput
              {...control}
              fieldLabel="새 비밀번호 확인"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              onBlur={() => setConfirmChecked(true)}
            />
          )}
        </Field>
        {errors.form !== null && (
          <FormError requestId={errors.form.requestId}>{errors.form.message}</FormError>
        )}
        <Button
          type="submit"
          variant="primary"
          size="md"
          className="mt-1"
          aria-busy={change.isPending}
          disabled={
            change.isPending ||
            currentPassword.length === 0 ||
            newPassword.length === 0 ||
            confirmPassword.length === 0
          }
        >
          {change.isPending ? (
            <LoaderCircle size={16} className="animate-spin" aria-hidden />
          ) : (
            <KeyRound size={16} aria-hidden />
          )}
          비밀번호 변경
        </Button>
      </form>
    </>
  )
}
