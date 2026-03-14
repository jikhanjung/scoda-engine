# SCODA Engine — Production Web Viewer (gunicorn only)
# Multi-stage build: builder → runtime

# ── Builder ──────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy core package first (changes less often)
COPY core/ core/
RUN pip install --no-cache-dir ./core

# Copy engine package
COPY pyproject.toml pyproject.toml
COPY scoda_engine/ scoda_engine/
RUN pip install --no-cache-dir ".[web]"

# ── Runtime ──────────────────────────────────────────────────
FROM python:3.12-slim

# Non-root user
RUN groupadd -r scoda && useradd -r -g scoda -d /app scoda

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy gunicorn config
COPY deploy/gunicorn.conf.py /app/gunicorn.conf.py

# Download all latest .scoda packages from Hub at build time
COPY deploy/fetch_packages.py /tmp/fetch_packages.py
ENV SCODA_HUB_SSL_VERIFY=0
RUN mkdir -p /data && python /tmp/fetch_packages.py --dest /data/ && \
    chown -R scoda:scoda /data && rm /tmp/fetch_packages.py

# Multi-package serving: all packages in /data/ are served simultaneously.
# Set SCODA_PACKAGE at runtime to force GET / redirect to a specific package.
ENV SCODA_MODE=viewer \
    SCODA_PORT=8081 \
    SCODA_WORKERS=2 \
    SCODA_LOG_LEVEL=info \
    SCODA_PATH=/data/ \
    SCODA_HUB_SYNC=1 \
    SCODA_HUB_SYNC_INTERVAL=86400

EXPOSE 8081

# Health check directly to gunicorn
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/healthz')" || exit 1

CMD ["gunicorn", "-c", "gunicorn.conf.py", "scoda_engine.serve_web:create_app()"]
