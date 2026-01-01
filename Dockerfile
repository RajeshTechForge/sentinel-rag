# ============================================
#       SENTINEL RAG - MULTI-STAGE DOCKERFILE
# ============================================
# Optimized for production with minimal image size,
# security best practices, and efficient layer caching.

# ----------------------------------------------
#  STAGE 1: BUILDER
#  - Install build dependencies
#  - Install Python packages with uv
#  - Download spaCy model for PII detection
# ----------------------------------------------
FROM python:3.11-slim AS builder

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # uv configuration
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install build dependencies (ordered for cache efficiency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first (layer caching optimization)
COPY pyproject.toml uv.lock ./
COPY README.md ./

# Create virtual environment and install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /app/.venv && \
    uv sync --frozen --no-dev --no-install-project

# Copy source code (after dependencies for better caching)
COPY src/ ./src/

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ----------------------------------------------
#  STAGE 2: RUNNER
#  - Minimal runtime image
#  - Non-root user for security
#  - Only production dependencies
# ----------------------------------------------
FROM python:3.11-slim AS runner

# Runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Application paths
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv" \
    PYTHONPATH="/app/src" \
    # Default PostgreSQL configuration (for local/docker-compose use)
    POSTGRES_HOST="postgres" \
    POSTGRES_PORT="5432" \
    POSTGRES_DB="sentinel_rag" \
    POSTGRES_USER="sentinel" \
    POSTGRES_PASSWORD="sentinel_secure_password" \
    # Sentinel configuration (uses bundled default if not provided)
    SENTINEL_CONFIG_PATH=""

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 sentinel && \
    useradd --uid 1000 --gid sentinel --shell /bin/bash --create-home sentinel

WORKDIR /app

# Copy virtual environment from builder (includes spaCy model)
COPY --from=builder --chown=sentinel:sentinel /app/.venv /app/.venv

# Copy source code
COPY --from=builder --chown=sentinel:sentinel /app/src /app/src

# Copy default configuration
COPY --chown=sentinel:sentinel src/sentinel_rag/config/default.json /app/config/default.json

# Switch to non-root user
USER sentinel

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "sentinel_rag.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
