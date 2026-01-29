FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY tool_pricing.yaml .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Use environment variable for port, default to 8000
ENV PORT=8000

CMD ["python", "-m", "mcp_server_lurky"]
