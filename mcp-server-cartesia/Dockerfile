# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Optional: keep for consistency
ENV UV_COMPILE_BYTECODE=1

# Copy project files first (including uv.lock if generated)
COPY . /app/

# Create virtual environment and install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    . /app/.venv/bin/activate && \
    uv pip install -e . && \
    uv pip install cartesia>=0.2.0 && \
    python -c "import cartesia; print(f'Builder stage: Cartesia {cartesia.__version__} installed successfully')"

# --- Final stage - minimal runtime image ---
FROM python:3.12-slim-bookworm

# Install ffmpeg system package required by pydub (transitive dependency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the installed virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
# Copy source code and package files
COPY --from=builder /app/src /app/src
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
COPY --from=builder /app/README.md /app/README.md

# Add the venv bin to the PATH for the final image
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Set PYTHONPATH properly
ENV PYTHONPATH="/app:/app/src"
ENV PYTHONPATH="/app:/app/src:${PYTHONPATH}"
# Install the package and dependencies in the final image
RUN . /app/.venv/bin/activate && \
    pip install -e . && \
    pip install cartesia>=0.2.0

# Set default port (can be overridden by environment variable)
ENV MCP_CARTESIA_PORT=8003

# Expose the default port
EXPOSE 8003

# Default directory for audio output inside the container
RUN mkdir -p /app/audio_outputs

# Verify Cartesia installation at build time in the final stage
RUN . /app/.venv/bin/activate && \
    python -c "import cartesia; print(f'Final stage: Cartesia version check: {cartesia.__version__}')" && \
    python -c "import sys; print(f'Python path: {sys.path}')"

# Run the server using the __main__.py entry point
ENTRYPOINT ["/app/.venv/bin/python", "-m", "mcp_server_cartesia"]
