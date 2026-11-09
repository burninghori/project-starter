"""FastAPI 앱 조립 — 로깅·DB 엔진·스토리지 수명, 미들웨어, 오류 처리기, 라우터."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.errors import register_error_handlers
from .api.router import build_api_router
from .config import settings
from .core.storage import close_storage, init_storage
from .db.engine import dispose_engine, init_engine
from .logging import get_logger, setup_logging
from .middleware.auth import AuthMiddleware
from .middleware.origin_check import OriginCheckMiddleware
from .middleware.request_context import RequestContextMiddleware

logger = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(settings.log_level)
    init_engine()
    init_storage()
    logger.info("api started", extra={"app_env": settings.app_env})
    try:
        yield
    finally:
        await dispose_engine()
        close_storage()
        logger.info("api stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        # 문서 화면도 화면 표기를 따른다(루트 CLAUDE.md 「서비스 명칭」 — 브라우저 탭 제목과 같게)
        title="App API",
        lifespan=lifespan,
        # 문서 경로는 /api 아래로 둬 API 와 같은 프록시 · 로드밸런서 규칙을 탄다. 인증 미들웨어가 로그인을 요구한다.
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    # 나중에 더한 미들웨어가 바깥이다 — 바깥부터 request_context → 출처 검사 → 인증. 출처 검사 · 인증의 403 · 401 에도
    # request_id · 접근 로그가 붙고, 출처 검사는 로그인 요청까지 DB 를 보기 전에 막는다
    app.add_middleware(AuthMiddleware)
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(build_api_router())
    return app


app = create_app()
