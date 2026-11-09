"""인증 도메인 서비스 — 자격 검증, 세션 대조, 비밀번호 변경·초기화, 계정 생성, 다른 도메인의 사람 칸에 쓰는 이름 조회.

세션을 첫 인자로 받고 HTTP 를 모른다. 라우터·미들웨어는 `SemanticHTTPException` 을 응답으로 바꾸고,
명령은 `AuthCommandError` 를 종료 코드로 바꾼다. bcrypt 는 CPU 를 수백 ms 쓰므로 스레드로 보낸다.
"""

import asyncio
from collections.abc import Collection
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, case, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.error_contract import SemanticHTTPException
from ...api.errors import violates_unique_constraint
from ...config import settings
from ...logging import get_logger
from .deps import ADMIN_ROLE, AuthUser
from .models import AppUser
from .passwords import burn_verification_cost, hash_password, password_rule_violation, verify_password
from .tokens import SessionClaims

logger = get_logger("domains.auth")

# 새 계정(시드 · 사용자 관리 API)의 로그인 직후 화면 경로 — 홈. 계정마다 다르게 두려면 사용자 관리 API 에 칸을 더한다
DEFAULT_PAGE_FOR_NEW_USERS = "/"
# 시드 관리자의 표시용 값
SEED_ADMIN_NAME = "관리자"
SEED_ADMIN_ORG = "시스템"


class AuthCommandError(Exception):
    """명령(seed_admin·reset_password)이 사용자에게 알리고 실패로 끝내는 오류."""


class LoginIdTakenError(AuthCommandError):
    def __init__(self, login_id: str) -> None:
        super().__init__(f"이미 있는 아이디: {login_id}")
        self.login_id = login_id


class UserNotFoundError(AuthCommandError):
    def __init__(self, login_id: str) -> None:
        super().__init__(f"없는 아이디: {login_id}")
        self.login_id = login_id


async def _find_by_login_id(db: AsyncSession, login_id: str) -> AppUser | None:
    return (await db.execute(select(AppUser).where(AppUser.login_id == login_id))).scalar_one_or_none()


async def user_names(db: AsyncSession, ids: Collection[int | None]) -> dict[int, str]:
    """사용자 id → 이름. 다른 도메인이 등록자 · 수정자 같은 사람 칸을 응답에 이름으로 실을 때 쓴다 — 행이 몇 개든 IN 조회 한 번.

    None(기록된 사람 없음 — 시드 행 등)은 찾지 않고, 찾을 id 가 없으면 쿼리를 보내지 않는다. 사람 칸은 FK 가 지키고
    사용자를 지우는 경로가 없으므로, 받은 id 는 모두 표에 있다 — 꺼낼 때 기본값 없이 `names[user_id]` 로 꺼낸다.
    """
    wanted = {user_id for user_id in ids if user_id is not None}
    if not wanted:
        return {}
    rows = (await db.execute(select(AppUser.id, AppUser.name).where(AppUser.id.in_(wanted)))).all()
    return {user_id: name for user_id, name in rows}


def _currently_locked(now: datetime) -> ColumnElement[bool]:
    """행 기준 「지금 잠겨 있다」 — 잠금 판정은 요청 시작 때 읽은 값이 아니라 UPDATE 하는 순간의 행으로 한다."""
    return AppUser.locked_until > now


async def _record_login_failure(db: AsyncSession, user_id: int, now: datetime) -> tuple[int, datetime | None]:
    """실패 한 번을 세고 commit 한다 — 로그인 실패는 예외로 끝나 요청 트랜잭션이 rollback 되므로 raise 전에 남겨야 한다.

    UPDATE 한 번이 행 잠금 아래에서 판정까지 한다: 이미 잠겼으면 아무것도 바꾸지 않고, 한도에 닿으면 잠그고 횟수를 0 으로 되돌린다.
    그래서 같은 계정에 동시에 몰린 실패도 한도까지만 세고 나머지는 잠금(429)이 된다. 반환: (실패 횟수, 잠금 시각).
    """
    locked = _currently_locked(now)
    next_count = AppUser.failed_login_count + 1
    reaches_limit = next_count >= settings.login_max_failures
    row = (
        await db.execute(
            update(AppUser)
            .where(AppUser.id == user_id)
            .values(
                failed_login_count=case((locked, AppUser.failed_login_count), (reaches_limit, 0), else_=next_count),
                locked_until=case(
                    (locked, AppUser.locked_until),
                    (reaches_limit, now + timedelta(minutes=settings.login_lock_minutes)),
                    else_=AppUser.locked_until,
                ),
            )
            .returning(AppUser.failed_login_count, AppUser.locked_until)
        )
    ).one()
    await db.commit()
    return row.failed_login_count, row.locked_until


async def _clear_login_failures(db: AsyncSession, user_id: int, now: datetime) -> datetime | None:
    """성공한 로그인의 실패 횟수를 0 으로 — 그 사이 다른 요청이 잠갔으면 바꾸지 않고 그 잠금 시각을 돌려준다(None = 잠기지 않음)."""
    locked = _currently_locked(now)
    locked_until = (
        await db.execute(
            update(AppUser)
            .where(AppUser.id == user_id)
            .values(
                failed_login_count=case((locked, AppUser.failed_login_count), else_=0),
                locked_until=case((locked, AppUser.locked_until), else_=None),
            )
            .returning(AppUser.locked_until)
        )
    ).scalar_one()
    return locked_until


def _locked_error(locked_until: datetime) -> SemanticHTTPException:
    return SemanticHTTPException(code="auth_login_locked", details={"lockedUntil": locked_until.isoformat()})


async def authenticate(db: AsyncSession, login_id: str, password: str) -> AppUser:
    """아이디 없음과 비밀번호 틀림을 같은 401 로 답하고, 둘 다 해시 검증 한 번만큼 시간을 쓴다.

    같은 계정의 연속 실패가 `LOGIN_MAX_FAILURES` 에 닿으면 `LOGIN_LOCK_MINUTES` 동안 429 다. 잠긴 동안의 시도는 비밀번호가 맞아도
    429 라 결과를 알려 주지 않는다 — 판정은 실패 기록 · 성공 정리의 UPDATE 가 행 잠금 아래에서 하므로 동시 요청에도 지켜진다.
    잠금은 계정 단위라 없는 아이디는 잠그지 않는다 — 출처(IP) 단위 제한은 앞단(프록시 · WAF)의 일이다.
    거부는 모두 warning 으로 남긴다(무차별 대입 · 잠금을 운영에서 볼 수 있게). 비밀번호는 남기지 않는다.

    DB 연결은 한 번에 하나만 쥔다. 행을 읽은 트랜잭션을 bcrypt(수백 ms) 전에 끝내 연결을 풀에 돌려준다 — 실패가 몰려도
    요청마다 연결을 쥔 채 기다리지 않는다.
    """
    now = datetime.now(UTC)
    user = await _find_by_login_id(db, login_id)
    await db.commit()
    if user is None:
        await asyncio.to_thread(burn_verification_cost, password)
        logger.warning("login rejected", extra={"login_id": login_id, "reason": "unknown login id"})
        raise SemanticHTTPException(code="auth_invalid_credentials")
    if user.locked_until is not None and user.locked_until > now:
        logger.warning(
            "login rejected", extra={"user_id": user.id, "reason": "locked", "locked_until": user.locked_until}
        )
        raise _locked_error(user.locked_until)
    if not await asyncio.to_thread(verify_password, password, user.password_hash):
        failed_login_count, locked_until = await _record_login_failure(db, user.id, now)
        if locked_until is not None and locked_until > now:
            logger.warning("login locked", extra={"user_id": user.id, "locked_until": locked_until})
            raise _locked_error(locked_until)
        logger.warning(
            "login rejected",
            extra={"user_id": user.id, "reason": "password mismatch", "failed_login_count": failed_login_count},
        )
        raise SemanticHTTPException(code="auth_invalid_credentials")
    if not user.is_active:
        logger.warning("login rejected", extra={"user_id": user.id, "reason": "inactive"})
        raise SemanticHTTPException(code="auth_user_inactive")
    locked_until = await _clear_login_failures(db, user.id, now)
    if locked_until is not None and locked_until > now:
        logger.warning("login rejected", extra={"user_id": user.id, "reason": "locked", "locked_until": locked_until})
        raise _locked_error(locked_until)
    return user


async def resolve_session(db: AsyncSession, claims: SessionClaims) -> AuthUser:
    """쿠키 claims 를 DB 행과 대조한다 — 없거나 버전이 다르면 401, 비활성이면 403(결정 0006)."""
    user = await db.get(AppUser, claims.user_id)
    if user is None:
        raise SemanticHTTPException(code="auth_required", diagnostic_message="session user no longer exists")
    if user.token_version != claims.token_version:
        raise SemanticHTTPException(code="auth_required", diagnostic_message="session revoked: token version changed")
    if not user.is_active:
        raise SemanticHTTPException(code="auth_user_inactive")
    return AuthUser.from_row(user)


async def change_password(db: AsyncSession, user: AuthUser, current_password: str, new_password: str) -> AuthUser:
    """본인 비밀번호 변경 — 기대 버전(`user.token_version`) 조건부로 `token_version +1`, 게이트 해제."""
    row = await db.get(AppUser, user.id)
    if row is None:
        raise SemanticHTTPException(code="auth_required", diagnostic_message="session user no longer exists")
    if not await asyncio.to_thread(verify_password, current_password, row.password_hash):
        # 세션은 유효하다 — 로그인 실패(401)가 아니라 입력 오류다. 화면은 현재 비밀번호 칸 아래에 보인다
        raise SemanticHTTPException(code="auth_current_password_invalid")
    violation = password_rule_violation(new_password)
    if violation is not None:
        raise SemanticHTTPException(code="auth_password_rule_violation", details={"rule": violation})

    new_hash = await asyncio.to_thread(hash_password, new_password)
    new_version = (
        await db.execute(
            update(AppUser)
            .where(AppUser.id == user.id, AppUser.token_version == user.token_version)
            .values(password_hash=new_hash, token_version=AppUser.token_version + 1, must_change_password=False)
            .returning(AppUser.token_version)
        )
    ).scalar_one_or_none()
    if new_version is None:
        # 그 사이 관리자가 초기화·회수해 버전이 올라갔다 — 이 세션으로는 더 진행할 수 없다
        raise SemanticHTTPException(code="auth_token_version_stale")
    await db.refresh(row)
    logger.info("password changed", extra={"user_id": row.id})
    return AuthUser.from_row(row)


async def create_user(
    db: AsyncSession,
    *,
    login_id: str,
    name: str,
    org: str,
    role: str,
    password: str,
    must_change_password: bool,
) -> AppUser:
    """계정 생성의 유일한 자리 — 시드 관리자와 사용자 관리 API 가 같이 쓴다. 같은 아이디가 있으면 `LoginIdTakenError`."""
    user = AppUser(
        login_id=login_id,
        name=name,
        org=org,
        role=role,
        is_active=True,
        password_hash=await asyncio.to_thread(hash_password, password),
        token_version=0,
        must_change_password=must_change_password,
        failed_login_count=0,
        locked_until=None,
        default_page=DEFAULT_PAGE_FOR_NEW_USERS,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        if violates_unique_constraint(exc, "uq_app_user_login_id"):
            raise LoginIdTakenError(login_id) from exc
        raise
    logger.info("user created", extra={"user_id": user.id, "login_id": login_id})
    return user


async def seed_admin(db: AsyncSession, *, login_id: str, password: str) -> AppUser | None:
    """관리자 시드(멱등). 이미 있으면 아무것도 바꾸지 않고 None."""
    if await _find_by_login_id(db, login_id) is not None:
        return None
    return await create_user(
        db,
        login_id=login_id,
        name=SEED_ADMIN_NAME,
        org=SEED_ADMIN_ORG,
        role=ADMIN_ROLE,
        password=password,
        must_change_password=True,
    )


async def reset_password(db: AsyncSession, *, login_id: str, new_password: str) -> AppUser:
    """관리자 초기화 명령(아이디로 찾는다). 동작은 `reset_password_row` 와 같다."""
    row = await _find_by_login_id(db, login_id)
    if row is None:
        raise UserNotFoundError(login_id)
    return await reset_password_row(db, row, new_password)


async def reset_password_row(db: AsyncSession, row: AppUser, new_password: str) -> AppUser:
    """관리자 초기화 — `token_version` 을 무조건 +1 해 기존 세션을 모두 끊고 첫 로그인 때 바꾸게 한다. 로그인 잠금도 푼다."""
    new_hash = await asyncio.to_thread(hash_password, new_password)
    await db.execute(
        update(AppUser)
        .where(AppUser.id == row.id)
        .values(
            password_hash=new_hash,
            token_version=AppUser.token_version + 1,
            must_change_password=True,
            failed_login_count=0,
            locked_until=None,
        )
    )
    await db.refresh(row)
    logger.info("password reset", extra={"user_id": row.id})
    return row
