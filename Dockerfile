# syntax=docker/dockerfile:1

FROM oven/bun:1 AS frontend

WORKDIR /app/frontend-dev
COPY frontend-dev/package.json frontend-dev/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend-dev/ ./
RUN bun run build


FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src/ ./src/
COPY --from=frontend /app/frontend-dev/dist/ ./src/fair_platform/frontend/dist/

RUN uv sync --frozen --no-dev

EXPOSE 3000

CMD ["sh", "-c", "fair serve --host 0.0.0.0 --port ${PORT:-3000} --no-update-check"]
