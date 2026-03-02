#!/usr/bin/env python3
"""
SCODA Desktop Viewer Launcher

Starts the web server and automatically opens the default browser.
"""

import webbrowser
from threading import Timer
import sys
import os


def open_browser(port):
    """Open default browser after a short delay."""
    webbrowser.open(f'http://localhost:{port}')


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=str, default=None,
                        help='Active package name')
    parser.add_argument('--scoda-path', type=str, default=None,
                        help='Path to a .scoda file to load')
    parser.add_argument('--db-path', type=str, default=None,
                        help='Raw .db file path for direct editing')
    parser.add_argument('--mode', default='viewer', choices=['viewer', 'admin'],
                        help='Server mode: viewer (read-only) or admin (CRUD enabled)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Server port (default: 8080)')
    args = parser.parse_args()

    # Validate: --mode admin requires --db-path (not --scoda-path)
    if args.mode == 'admin' and not args.db_path:
        print("Error: --mode admin requires --db-path (cannot use --scoda-path)", file=sys.stderr)
        sys.exit(1)
    if args.db_path and args.scoda_path:
        print("Error: --db-path and --scoda-path are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    port = args.port

    print("=" * 60)
    print("SCODA Desktop Viewer")
    print("=" * 60)
    if args.db_path:
        print(f"Database: {args.db_path}")
        print(f"Mode: {args.mode}")
    elif args.scoda_path:
        print(f"Loading: {args.scoda_path}")
    elif args.package:
        print(f"Package: {args.package}")
    print(f"Server running at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Open browser after 1.5 seconds
    Timer(1.5, lambda: open_browser(port)).start()

    # Resolve paths before chdir
    resolved_db_path = os.path.abspath(args.db_path) if args.db_path else None
    resolved_scoda_path = os.path.abspath(args.scoda_path) if args.scoda_path else None

    # Import and run FastAPI app
    try:
        import uvicorn

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(base_path)

        # Set mode before importing app
        os.environ['SCODA_MODE'] = args.mode
        os.environ.setdefault('SCODA_ENABLE_MCP', '1')

        if resolved_db_path:
            from scoda_engine_core import _set_paths_for_testing
            # Use raw DB path — overlay is adjacent
            db_dir = os.path.dirname(resolved_db_path)
            db_name = os.path.splitext(os.path.basename(resolved_db_path))[0]
            overlay_path = os.path.join(db_dir, f"{db_name}_overlay.db")
            _set_paths_for_testing(resolved_db_path, overlay_path)
        elif resolved_scoda_path:
            from scoda_engine_core import register_scoda_path
            register_scoda_path(resolved_scoda_path)
        elif args.package:
            from scoda_engine_core import set_active_package
            set_active_package(args.package)

        from .app import app
        uvicorn.run(app, host='127.0.0.1', port=port, log_level='info')
    except ImportError as e:
        print(f"Error: Could not import app: {e}", file=sys.stderr)
        print("Make sure app.py is in the same directory.", file=sys.stderr)
        input("\nPress Enter to exit...")
        sys.exit(1)
    except OSError as e:
        print(f"Error: Could not start server: {e}", file=sys.stderr)
        print(f"Port {port} might already be in use.", file=sys.stderr)
        input("\nPress Enter to exit...")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nShutting down SCODA Desktop...")
        sys.exit(0)
