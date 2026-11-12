FROM ghcr.io/astral-sh/uv:0.9.7 AS uv
FROM python:3.11-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.11-slim AS runtime
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ANONYMIZED_TELEMETRY=False
WORKDIR /app
RUN useradd --uid 10001 --create-home architect \
    && mkdir -p /app/data /app/knowledge_base /app/generated_projects \
    && chown -R architect:architect /app
COPY --from=builder /app/.venv ./.venv
COPY --chown=architect:architect app ./app
COPY --chown=architect:architect migrations ./migrations
COPY --chown=architect:architect alembic.ini ./
USER architect
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
