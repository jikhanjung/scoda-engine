"""Gunicorn configuration for SCODA Web Viewer."""

import os

# Worker class — uvicorn ASGI worker
worker_class = "uvicorn.workers.UvicornWorker"

# Number of worker processes
workers = int(os.environ.get("SCODA_WORKERS", "2"))

# Bind address (localhost only — nginx proxies from port 80)
bind = f"127.0.0.1:{os.environ.get('SCODA_PORT', '8000')}"

# Drop privileges to non-root user
user = "scoda"
group = "scoda"

# Preload disabled: workers run as 'scoda' user and must each load the app
# (preload runs as root before privilege drop, causing temp file permission issues)
preload_app = False

# Worker timeout (seconds)
timeout = 120

# Logging
accesslog = "-"  # stdout
loglevel = os.environ.get("SCODA_LOG_LEVEL", "info")
