"""`python -m app` 진입점 — 설정의 host·port 로 uvicorn 을 띄운다.

로컬·컨테이너 모두 이 한 줄로 기동한다. 포트는 `APP_PORT` 가 정한다(컨테이너는 Dockerfile ENV).
"""

import uvicorn

from app.config import settings
from app.logging import setup_logging


def main() -> None:
    # uvicorn 자체 로그(기동·종료)도 앱과 같은 형식으로 나가게 한다. reload 의 자식 프로세스는 앱 lifespan 이 다시 세운다.
    setup_logging(settings.log_level)
    # reload 가 워커 프로세스에서 다시 import 하려면 객체가 아니라 import 경로 문자열이어야 한다.
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
        # 직접 접근 로그를 남긴다(middleware.request_context)
        access_log=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
