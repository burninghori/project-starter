"""API 라우터 조립의 단일 지점.

- `/api/health` — 상태 확인(버전 없음, 로드밸런서 헬스체크 경로).
- `/api/v1/...` — 업무 API. 도메인 라우터를 `_DOMAIN_ROUTERS` 에 한 줄씩 더한다.

도메인 라우터는 `app/domains/<domain>/router.py` 의 `router` 이고, 자기 prefix(`/auth` 등)를 갖는다.
"""

from fastapi import APIRouter

from ..domains.auth.router import router as auth_router
from ..domains.auth.users_router import router as users_router
from . import health

# 도메인 라우터 목록. 예: from ..domains.reports.router import router as reports_router
_DOMAIN_ROUTERS: list[APIRouter] = [
    auth_router,
    users_router,
]


def build_api_router() -> APIRouter:
    api = APIRouter(prefix="/api")
    api.include_router(health.router)

    v1 = APIRouter(prefix="/v1")
    for domain_router in _DOMAIN_ROUTERS:
        v1.include_router(domain_router)
    api.include_router(v1)
    return api
