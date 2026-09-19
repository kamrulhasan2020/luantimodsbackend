# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12-slim

# ---- base ----
FROM python:${PYTHON_VERSION} AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app

# ---- builder: resolves dependencies from the lockfile into /opt/venv ----
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- dev: adds dev dependencies, hot reload ----
FROM builder AS dev
RUN uv sync --frozen
COPY . .
RUN chmod +x docker/entrypoint.sh
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--reload", "app.main:app"]

# ---- prod: slim runtime, no uv, non-root ----
FROM base AS prod
COPY --from=builder /opt/venv /opt/venv
COPY . .
RUN chmod +x docker/entrypoint.sh \
    && useradd --create-home --no-log-init appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app/data
USER appuser
EXPOSE 8000
ENTRYPOINT ["/app/docker/entrypoint.sh"]
# One worker on purpose: the rate limiter is in-memory, so it's only accurate per process.
CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "app.main:app"]
