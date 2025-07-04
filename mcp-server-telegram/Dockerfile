# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1

# Copy project files first
COPY . /app/

# Create venv and install dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install requests && \
    uv pip install -e .

# Final stage - minimal runtime image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy only the installed virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv
# Copy source code including the src directory
COPY --from=builder /app/src /app/src

# Add the venv bin to the PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app/src"
ENV MCP_TELEGRAM_PORT=8002

# Expose ports for the Telegram MCP server
EXPOSE 8002

# ---->HEALTHCHECK <----
    HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the server
CMD ["python", "-m", "mcp_server_telegram"]
