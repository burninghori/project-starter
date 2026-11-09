"""상태 확인 endpoint.

- `GET /api/health` — 프로세스 생존만 본다. 로드밸런서 헬스체크가 수 초마다 부르므로 DB·스토리지를 건드리지 않는다.
- `GET /api/health/ready` — DB 연결과 스토리지 버킷(`HeadBucket`)까지 확인한다. 배포 직후 점검·로컬 확인용.
  둘 중 하나라도 닿지 않으면 503 이고, 어느 쪽인지는 오류 code 가 말한다.
"""

import asyncio

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..core.storage import StorageUnavailableError, get_storage
from ..db.engine import get_engine
from ..logging import get_logger
from .error_contract import SemanticHTTPException
from .schemas import ApiBase

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger("api.health")


class HealthOut(ApiBase):
    status: str


@router.get("")
async def health() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/ready")
async def ready() -> HealthOut:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError) as exc:
        logger.warning("database not ready", extra={"error_class": type(exc).__name__})
        raise SemanticHTTPException(
            code="database_unavailable",
            diagnostic_message=f"{type(exc).__name__}: {exc}",
        ) from exc
    try:
        # boto3 는 동기 호출이라 이벤트 루프를 막지 않게 스레드로 보낸다
        await asyncio.to_thread(get_storage().check_bucket)
    except StorageUnavailableError as exc:
        logger.warning("storage not ready", extra={"error_class": type(exc.__cause__).__name__})
        raise SemanticHTTPException(code="storage_unavailable", diagnostic_message=str(exc)) from exc
    return HealthOut(status="ok")
