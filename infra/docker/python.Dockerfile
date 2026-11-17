FROM ghcr.io/astral-sh/uv:0.7.13 AS uv
FROM python:3.11-slim AS base
COPY --from=uv /uv /uvx /bin/
WORKDIR /workspace
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/services/api:/workspace/services/worker:/workspace/services/inference:/workspace/services/edge-agent:/workspace/ai:/workspace/packages/core
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/workspace/.venv/bin:$PATH"
COPY services services
COPY packages packages
COPY ai ai
COPY database database
RUN useradd --uid 10001 --create-home platform
USER platform
FROM base AS development
USER root
RUN uv sync --frozen
USER platform
