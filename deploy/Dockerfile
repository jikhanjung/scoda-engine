# SCODA Engine — Production Web Viewer (single container: nginx + gunicorn)
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

# Install nginx
RUN apt-get update && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

# Non-root user (created after nginx so we can adjust permissions)
RUN groupadd -r scoda && useradd -r -g scoda -d /app scoda

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# Copy gunicorn config
COPY deploy/gunicorn.conf.py /app/gunicorn.conf.py

# Copy nginx config, static files, and error page
COPY deploy/nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY scoda_engine/static/ /usr/share/nginx/html/static/
COPY deploy/nginx/50x.html /usr/share/nginx/html/50x.html

# Remove default nginx site config
RUN rm -f /etc/nginx/sites-enabled/default

# Copy entrypoint (sed strips Windows CRLF if present)
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Download all latest .scoda packages from Hub at build time
COPY deploy/fetch_packages.py /tmp/fetch_packages.py
RUN mkdir -p /data && python /tmp/fetch_packages.py --dest /data/ && \
    chown -R scoda:scoda /data && rm /tmp/fetch_packages.py

# Ensure nginx runtime directories exist
RUN mkdir -p /var/lib/nginx/body /var/log/nginx

# Default package (set at build time, overridable at runtime)
ARG DEFAULT_PACKAGE=trilobase-assertion
ENV SCODA_MODE=viewer \
    SCODA_PORT=8000 \
    SCODA_WORKERS=2 \
    SCODA_LOG_LEVEL=info \
    SCODA_PATH=/data/ \
    SCODA_PACKAGE=${DEFAULT_PACKAGE}

EXPOSE 80

# Health check via nginx on port 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:80/healthz')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
