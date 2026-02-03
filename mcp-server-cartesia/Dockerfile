FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Install project dependencies using mounted uv.lock (ensure it exists locally)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Install the project itself (done for layer caching optimization)
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# --- Dev stage --- #
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS dev

WORKDIR /app

ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

# Copy the application package from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Additionally install dev and debug dependencies without removing the project
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv pip install --group dev --group debug

# Make container use python installed inside the venv
ENV PATH="/app/.venv/bin:$PATH"

CMD ["tail", "-f", "/dev/null"]

# --- Production stage --- #
FROM python:3.12-slim-bookworm AS prod

WORKDIR /app

# Install ffmpeg required by pydub (transitive dependency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy the application package from the builder stage
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# Default directory for audio output inside the container
RUN mkdir -p /app/audio_outputs

CMD ["python", "-m", "mcp_server_cartesia", "--host", "0.0.0.0", "--port", "8000"]
