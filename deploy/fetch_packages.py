#!/usr/bin/env python3
"""
fetch_packages.py — Download all latest .scoda packages from Hub

Build-time script for Docker: fetches the Hub index, then downloads
all packages (latest version) with their dependencies.

Uses scoda_engine_core.hub_client functions (fetch_hub_index, download_package)
which include SHA-256 verification.

Usage:
    python deploy/fetch_packages.py --dest /data/
"""

import argparse
import os
import sys

# Ensure the repo root is importable (for Docker build context)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from scoda_engine_core.hub_client import (
    fetch_hub_index,
    download_package,
    HubError,
)


def fetch_all_packages(dest_dir, hub_url=None, timeout=120):
    """Download all latest .scoda packages from Hub.

    Args:
        dest_dir: Directory to save .scoda files.
        hub_url: Optional Hub index URL override.
        timeout: Download timeout in seconds.

    Returns:
        List of (name, version, path) tuples for downloaded packages.
    """
    os.makedirs(dest_dir, exist_ok=True)

    print("Fetching Hub index...")
    index = fetch_hub_index(hub_url=hub_url, timeout=timeout)
    packages = index.get("packages", {})

    if not packages:
        print("WARNING: No packages found in Hub index")
        return []

    print(f"Found {len(packages)} package(s) in Hub index")
    print()

    downloaded = []
    for pkg_name, pkg_data in packages.items():
        latest_version = pkg_data.get("latest", "")
        if not latest_version:
            print(f"  SKIP {pkg_name}: no latest version")
            continue

        latest_entry = pkg_data.get("versions", {}).get(latest_version, {})
        download_url = latest_entry.get("download_url")
        if not download_url:
            print(f"  SKIP {pkg_name}: no download URL")
            continue

        expected_sha256 = latest_entry.get("sha256")

        print(f"  Downloading {pkg_name} v{latest_version}...")
        try:
            path = download_package(
                download_url=download_url,
                dest_dir=dest_dir,
                expected_sha256=expected_sha256,
                timeout=timeout,
            )
            size = os.path.getsize(path)
            downloaded.append((pkg_name, latest_version, path))
            print(f"    OK: {os.path.basename(path)} ({size:,} bytes)")
        except HubError as e:
            print(f"    FAIL: {e}", file=sys.stderr)

    return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Download all latest .scoda packages from Hub")
    parser.add_argument("--dest", type=str, default="/data/",
                        help="Destination directory (default: /data/)")
    parser.add_argument("--hub-url", type=str, default=None,
                        help="Hub index URL override")
    parser.add_argument("--timeout", type=int, default=120,
                        help="Download timeout in seconds (default: 120)")
    args = parser.parse_args()

    print("=" * 60)
    print("SCODA Hub Package Fetcher")
    print("=" * 60)
    print(f"Destination: {args.dest}")
    print()

    try:
        downloaded = fetch_all_packages(
            dest_dir=args.dest,
            hub_url=args.hub_url,
            timeout=args.timeout,
        )
    except HubError as e:
        print(f"\nFATAL: {e}", file=sys.stderr)
        sys.exit(1)

    print()
    print("=" * 60)
    print(f"Summary: {len(downloaded)} package(s) downloaded")
    for name, version, path in downloaded:
        size = os.path.getsize(path)
        print(f"  {name} v{version} — {os.path.basename(path)} ({size:,} bytes)")
    print("=" * 60)

    if not downloaded:
        print("WARNING: No packages were downloaded", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
