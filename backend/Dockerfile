# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENCV_LOG_LEVEL=ERROR \
    FA_RUN_MIGRATIONS_ON_STARTUP=false \
    FORWARDED_ALLOW_IPS="*" \
    WEB_CONCURRENCY=2 \
    FA_MODELS__DIRECTORY=/app/models

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# models change rarely -> separate cached layer
COPY scripts ./scripts
RUN python scripts/download_models.py --dest /app/models

COPY pyproject.toml ./
COPY app ./app
COPY evaluation ./evaluation
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations

RUN useradd --system --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown appuser /app/data
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health/live' % os.environ.get('PORT', '8000'))"

CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY} --proxy-headers"]
