#!/usr/bin/env python3
"""
SCODA Production Web Viewer

Production entry point for serving .scoda packages via gunicorn/uvicorn.
Forces viewer mode (read-only) and disables MCP.

Usage:
    # Direct run
    python -m scoda_engine.serve_web

    # With gunicorn
    gunicorn 'scoda_engine.serve_web:create_app()'

Environment variables:
    SCODA_PATH      — Path to .scoda file or directory (required)
    SCODA_PACKAGE   — Active package name when SCODA_PATH is a directory
    SCODA_PORT      — Server port (default: 8000)
    SCODA_WORKERS   — Number of worker processes (default: 2)
    SCODA_LOG_LEVEL — Log level (default: info)
    SCODA_HUB_SYNC  — Set to "1" to sync packages from Hub on startup
    SCODA_HUB_SYNC_INTERVAL — Periodic sync interval in seconds (default: 0 = disabled)
                               Example: 86400 = once a day
"""

import logging
import os
import sys
import threading
import time as _time

logger = logging.getLogger(__name__)

# Background scheduler state
_hub_sync_timer = None


def _sync_hub_packages(scoda_path):
    """Sync .scoda packages from Hub before starting the server.

    Fetches the Hub index, compares with local packages in scoda_path,
    and downloads any new or updated packages.

    Only runs when SCODA_HUB_SYNC=1 and scoda_path is a directory.
    """
    from scoda_engine_core.hub_client import (
        fetch_hub_index,
        compare_with_local,
        download_package,
        HubError,
    )
    from scoda_engine_core import get_registry

    ssl_noverify = os.environ.get('SCODA_HUB_SSL_VERIFY', '1').strip() == '0'

    try:
        index = fetch_hub_index(ssl_noverify=ssl_noverify)
    except HubError as e:
        logger.warning("Hub sync: failed to fetch index — %s", e)
        return 0

    # Scan local packages for comparison
    registry = get_registry()
    registry.scan(scoda_path)
    local_packages = registry.list_packages()

    comparison = compare_with_local(index, local_packages)
    to_download = comparison['available'] + comparison['updatable']

    if not to_download:
        logger.info("Hub sync: all packages up to date")
        return 0

    for pkg in to_download:
        name = pkg['name']
        version = pkg['hub_version']
        entry = pkg['hub_entry']
        download_url = entry.get('download_url')
        if not download_url:
            continue
        local_ver = pkg.get('local_version', '(new)')
        logger.info("Hub sync: downloading %s %s → %s", name, local_ver, version)
        try:
            download_package(
                download_url=download_url,
                dest_dir=scoda_path,
                expected_sha256=entry.get('sha256'),
                ssl_noverify=ssl_noverify,
            )
        except HubError as e:
            logger.warning("Hub sync: failed to download %s — %s", name, e)

    # Re-scan after downloads so registry picks up new files
    registry.scan(scoda_path)
    logger.info("Hub sync: done — %d package(s) synced", len(to_download))
    return len(to_download)


def _start_periodic_sync(scoda_path, interval):
    """Start a background thread that runs Hub sync at the given interval."""
    global _hub_sync_timer

    def _run():
        global _hub_sync_timer
        logger.info("Hub sync (scheduled): running periodic check")
        try:
            _sync_hub_packages(scoda_path)
        except Exception as e:
            logger.warning("Hub sync (scheduled): error — %s", e)
        # Re-schedule
        _hub_sync_timer = threading.Timer(interval, _run)
        _hub_sync_timer.daemon = True
        _hub_sync_timer.start()

    _hub_sync_timer = threading.Timer(interval, _run)
    _hub_sync_timer.daemon = True
    _hub_sync_timer.start()
    logger.info("Hub sync: periodic sync enabled — every %d seconds", interval)


def create_app():
    """Application factory for gunicorn.

    Forces viewer mode and disables MCP, then loads the .scoda package
    and returns the FastAPI app.

    SCODA_PATH can be:
      - A .scoda file → register that single file (original behavior)
      - A directory → scan for all .scoda files, select active via SCODA_PACKAGE
    """
    # Force read-only viewer mode (MCP disabled by default, no action needed)
    os.environ['SCODA_MODE'] = 'viewer'
    os.environ['SCODA_ENGINE_NAME'] = 'SCODA Server'

    scoda_path = os.environ.get('SCODA_PATH')
    if scoda_path:
        if os.path.isdir(scoda_path):
            # Hub sync: download new/updated packages before scanning
            if os.environ.get('SCODA_HUB_SYNC', '0').strip() == '1':
                _sync_hub_packages(scoda_path)
            # Directory mode: scan all .scoda files, serve all via pkg_router
            from scoda_engine_core import get_registry
            registry = get_registry()
            registry.scan(scoda_path)
            packages = registry.list_packages()
            if packages:
                # Validate SCODA_PACKAGE if set (used by GET / redirect)
                selected = os.environ.get('SCODA_PACKAGE')
                if selected:
                    matching = [p for p in packages if p['name'] == selected]
                    if not matching:
                        available = ', '.join(p['name'] for p in packages)
                        print(f"WARNING: SCODA_PACKAGE='{selected}' not found. "
                              f"Available: {available}", file=sys.stderr)
        else:
            # Single file mode (original behavior)
            from scoda_engine_core import register_scoda_path
            register_scoda_path(scoda_path)

    # Start periodic Hub sync if interval is set
    sync_interval = int(os.environ.get('SCODA_HUB_SYNC_INTERVAL', '0'))
    if sync_interval > 0 and scoda_path and os.path.isdir(scoda_path):
        _start_periodic_sync(scoda_path, sync_interval)

    from scoda_engine.app import app

    # Register /api/hub/sync endpoint for on-demand sync
    if scoda_path and os.path.isdir(scoda_path):
        _scoda_path = scoda_path  # capture for closure

        @app.post('/api/hub/sync')
        def hub_sync_endpoint():
            """Trigger Hub sync on demand."""
            try:
                synced = _sync_hub_packages(_scoda_path)
                return {"status": "ok", "synced": synced or 0}
            except Exception as e:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    {"status": "error", "detail": str(e)},
                    status_code=500,
                )

    return app


def main():
    """CLI entry point — run directly with uvicorn (no gunicorn needed)."""
    import argparse

    parser = argparse.ArgumentParser(description='SCODA Production Web Viewer')
    parser.add_argument('--scoda-path', type=str, default=None,
                        help='Path to a .scoda file (overrides SCODA_PATH env)')
    parser.add_argument('--port', type=int, default=None,
                        help='Server port (overrides SCODA_PORT env, default: 8000)')
    parser.add_argument('--workers', type=int, default=None,
                        help='Number of workers (overrides SCODA_WORKERS env, default: 2)')
    parser.add_argument('--log-level', type=str, default=None,
                        help='Log level (overrides SCODA_LOG_LEVEL env, default: info)')
    args = parser.parse_args()

    # CLI args override env vars
    if args.scoda_path:
        os.environ['SCODA_PATH'] = os.path.abspath(args.scoda_path)
    if args.port:
        os.environ['SCODA_PORT'] = str(args.port)
    if args.workers:
        os.environ['SCODA_WORKERS'] = str(args.workers)
    if args.log_level:
        os.environ['SCODA_LOG_LEVEL'] = args.log_level

    port = int(os.environ.get('SCODA_PORT', '8000'))
    workers = int(os.environ.get('SCODA_WORKERS', '2'))
    log_level = os.environ.get('SCODA_LOG_LEVEL', 'info')

    scoda_path = os.environ.get('SCODA_PATH')
    if not scoda_path:
        print("Error: SCODA_PATH environment variable or --scoda-path argument required",
              file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("SCODA Web Viewer (Production)")
    print("=" * 60)
    print(f"Package: {scoda_path}")
    if os.path.isdir(scoda_path):
        selected = os.environ.get('SCODA_PACKAGE', '(auto)')
        print(f"Mode:    directory scan (active: {selected})")
    print(f"Bind:    0.0.0.0:{port}")
    print(f"Workers: {workers}")
    print(f"Mode:    viewer (read-only)")
    print("=" * 60)
    print()

    import uvicorn
    uvicorn.run(
        'scoda_engine.serve_web:create_app',
        host='0.0.0.0',
        port=port,
        workers=workers,
        log_level=log_level,
        factory=True,
    )


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down SCODA Web Viewer...")
        sys.exit(0)
