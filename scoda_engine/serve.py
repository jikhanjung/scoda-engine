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
    parser.add_argument('--port', type=int, default=8080,
                        help='Server port (default: 8080)')
    args = parser.parse_args()

    port = args.port

    print("=" * 60)
    print("SCODA Desktop Viewer")
    print("=" * 60)
    if args.scoda_path:
        print(f"Loading: {args.scoda_path}")
    elif args.package:
        print(f"Package: {args.package}")
    print(f"Server running at: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    # Open browser after 1.5 seconds
    Timer(1.5, lambda: open_browser(port)).start()

    # Import and run FastAPI app
    try:
        import uvicorn

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        os.chdir(base_path)

        if args.scoda_path:
            from scoda_engine_core import register_scoda_path
            register_scoda_path(args.scoda_path)
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
