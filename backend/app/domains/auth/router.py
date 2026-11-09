"""인증 API — api.md 「인증」. 로그인만 미들웨어 제외 경로이고 나머지는 로그인된 사용자가 부른다."""

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.deps import DbDep
from ...logging import get_logger
from . import service
from .deps import AuthUser, CurrentUser
from .schemas import AuthUserEnvelope, AuthUserOut, LoginIn, PasswordChangeIn
from .tokens import clear_session_cookie, issue_token, set_session_cookie

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger("domains.auth.router")


@router.post("/login")
async def login(body: LoginIn, response: Response, db: AsyncSession = DbDep) -> AuthUserEnvelope:
    user = await service.authenticate(db, body.login_id, body.password)
    set_session_cookie(response, issue_token(user.id, user.token_version))
    logger.info("login", extra={"user_id": user.id})
    return AuthUserEnvelope(user=AuthUserOut.model_validate(user))


@router.post("/logout", status_code=204)
async def logout(user: AuthUser = CurrentUser) -> Response:
    # 서버에 세션 상태가 없으므로 쿠키를 지우는 것이 로그아웃이다(결정 0006)
    response = Response(status_code=204)
    clear_session_cookie(response)
    logger.info("logout", extra={"user_id": user.id})
    return response


@router.get("/me")
async def me(user: AuthUser = CurrentUser) -> AuthUserEnvelope:
    return AuthUserEnvelope(user=AuthUserOut.model_validate(user))


@router.post("/password")
async def change_password(
    body: PasswordChangeIn,
    response: Response,
    user: AuthUser = CurrentUser,
    db: AsyncSession = DbDep,
) -> AuthUserEnvelope:
    updated = await service.change_password(db, user, body.current_password, body.new_password)
    # 버전이 올라갔으니 자기 쿠키를 새 버전으로 바꿔 준다
    set_session_cookie(response, issue_token(updated.id, updated.token_version))
    return AuthUserEnvelope(user=AuthUserOut.model_validate(updated))
