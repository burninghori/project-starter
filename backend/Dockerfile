# api·worker·마이그레이션이 모두 이 이미지 하나로 돈다(명령만 다르다).
#   api        : python -m app            (기본 CMD)
#   worker     : python -m app.worker
#   migrate    : alembic upgrade head

FROM python:3.13-slim AS base
WORKDIR /app

FROM base AS deps
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-hashes --no-dev -o requirements.txt \
    && pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

# 배포 환경이 넣지 않는 실행 설정은 이미지가 정한다. 컨테이너 안 포트는 8000 이다.
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    APP_RELOAD=false \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser
CMD ["python", "-m", "app"]
