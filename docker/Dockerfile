# ==============================================================================
# SIH26146 - Multi-stage Production Dockerfile (Linux Target)
# Stage 1: Build React Frontend
# Stage 2: Python FastAPI + Analytical Engine Core
# ==============================================================================

FROM node:22-slim AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DUCKDB_PATH=/app/data/database/sih26146.duckdb \
    OLLAMA_BASE_URL=http://ollama:11434 \
    OLLAMA_MODEL=nemotron-3.5-lightning

WORKDIR /app

# Install system dependencies (build-essential for C extensions if required)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create data directories
RUN mkdir -p /app/data/raw /app/data/processed /app/data/sample /app/data/database

# Copy pre-compiled frontend static assets into frontend/dist
COPY --from=frontend-builder /build/dist ./frontend/dist

EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

WORKDIR /app/backend
CMD ["python", "run.py"]
