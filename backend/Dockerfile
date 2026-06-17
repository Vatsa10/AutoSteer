# =============================================================================
# AutoSteer Backend — Production Dockerfile
# Uses multi-stage build to minimize final image size.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — builder: install build deps + Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install core Python dependencies first (cached layer).
COPY pyproject.toml .
RUN pip install --no-cache-dir --user .

# Now copy the application source and install the package itself.
COPY . .
RUN pip install --no-cache-dir --user .

# ---------------------------------------------------------------------------
# Stage 2 — runtime: minimal image with only runtime deps
# ---------------------------------------------------------------------------
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder stage.
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application source (needed for the installed package to reference assets).
COPY . .

# Create a non-root user and switch to it for security.
RUN addgroup --system --gid 1001 autosteer && \
    adduser --system --uid 1001 --gid 1001 autosteer && \
    chown -R autosteer:autosteer /app
USER autosteer

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl --fail http://localhost:8000/api/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
