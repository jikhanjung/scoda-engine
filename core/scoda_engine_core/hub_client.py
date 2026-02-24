"""
hub_client.py — SCODA Hub client (pure stdlib)

Provides functions to fetch the Hub package index, compare with local
packages, resolve dependency download order, and download .scoda files
with SHA-256 verification.

No external dependencies — uses only Python stdlib (urllib, hashlib, json).
"""

import hashlib
import json
import logging
import os
import tempfile
import urllib.error
import urllib.request

from .scoda_package import _parse_semver

logger = logging.getLogger(__name__)

DEFAULT_HUB_URL = "https://jikhanjung.github.io/scoda-engine/index.json"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HubError(Exception):
    """Base exception for Hub operations."""


class HubConnectionError(HubError):
    """Raised when the Hub index cannot be fetched."""


class HubChecksumError(HubError):
    """Raised when a downloaded file's SHA-256 does not match."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_hub_index(hub_url=None, timeout=10):
    """Fetch and parse the Hub index.json.

    Args:
        hub_url: URL to index.json. Defaults to SCODA_HUB_URL env var
                 or the hardcoded default.
        timeout: HTTP request timeout in seconds.

    Returns:
        Parsed index dict.

    Raises:
        HubConnectionError: On network or parse failure.
    """
    url = hub_url or os.environ.get("SCODA_HUB_URL") or DEFAULT_HUB_URL
    logger.info("Fetching Hub index from %s", url)

    req = urllib.request.Request(url, headers={
        "User-Agent": "ScodaDesktop",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        index = json.loads(data)
        pkg_count = len(index.get("packages", {}))
        logger.info("Hub index fetched: %d package(s)", pkg_count)
        return index
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        raise HubConnectionError(f"Failed to fetch Hub index: {e}") from e
    except (json.JSONDecodeError, ValueError) as e:
        raise HubConnectionError(f"Invalid Hub index JSON: {e}") from e


def compare_with_local(hub_index, local_packages):
    """Compare Hub packages with locally installed packages.

    Args:
        hub_index: Parsed Hub index dict (from fetch_hub_index).
        local_packages: List of local package info dicts, each with
                        at least 'name' and 'version' keys
                        (as returned by PackageRegistry.list_packages()).

    Returns:
        dict with keys:
          - available: list of Hub packages not installed locally
          - updatable: list of Hub packages with a newer version than local
          - up_to_date: list of Hub packages that match the local version
        Each list item is a dict with: name, hub_version, hub_entry,
        and optionally local_version (for updatable/up_to_date).
    """
    hub_packages = hub_index.get("packages", {})
    local_map = {pkg["name"]: pkg["version"] for pkg in local_packages}

    available = []
    updatable = []
    up_to_date = []

    for pkg_name, pkg_data in hub_packages.items():
        latest_version = pkg_data.get("latest", "")
        if not latest_version:
            continue
        latest_entry = pkg_data.get("versions", {}).get(latest_version, {})
        if not latest_entry.get("download_url"):
            continue

        if pkg_name not in local_map:
            available.append({
                "name": pkg_name,
                "hub_version": latest_version,
                "hub_entry": latest_entry,
            })
        else:
            local_ver = local_map[pkg_name]
            try:
                hub_semver = _parse_semver(latest_version)
                local_semver = _parse_semver(local_ver)
            except ValueError:
                continue

            if hub_semver > local_semver:
                updatable.append({
                    "name": pkg_name,
                    "hub_version": latest_version,
                    "local_version": local_ver,
                    "hub_entry": latest_entry,
                })
            else:
                up_to_date.append({
                    "name": pkg_name,
                    "hub_version": latest_version,
                    "local_version": local_ver,
                    "hub_entry": latest_entry,
                })

    return {
        "available": available,
        "updatable": updatable,
        "up_to_date": up_to_date,
    }


def download_package(download_url, dest_dir, expected_sha256=None,
                     progress_callback=None, timeout=60):
    """Download a .scoda package file.

    Downloads to a .tmp file first, verifies SHA-256 if provided,
    then renames to the final filename.

    Args:
        download_url: URL to the .scoda file.
        dest_dir: Directory to save the file in.
        expected_sha256: Expected SHA-256 hex digest (or None to skip).
        progress_callback: Optional callable(bytes_downloaded, total_bytes).
                           total_bytes may be 0 if Content-Length is absent.
        timeout: HTTP request timeout in seconds.

    Returns:
        Path to the downloaded .scoda file.

    Raises:
        HubConnectionError: On network failure.
        HubChecksumError: On SHA-256 mismatch.
    """
    filename = download_url.rsplit("/", 1)[-1]
    if not filename.endswith(".scoda"):
        filename += ".scoda"
    dest_path = os.path.join(dest_dir, filename)

    logger.info("Downloading %s to %s", download_url, dest_dir)

    req = urllib.request.Request(download_url, headers={
        "User-Agent": "ScodaDesktop",
    })

    # Use a named temp file in the same directory for atomic rename
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dest_dir)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            sha256 = hashlib.sha256()
            downloaded = 0

            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                os.write(tmp_fd, chunk)
                sha256.update(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)

        os.close(tmp_fd)
        tmp_fd = None

        # Verify checksum
        if expected_sha256:
            actual = sha256.hexdigest()
            if actual != expected_sha256:
                os.unlink(tmp_path)
                raise HubChecksumError(
                    f"SHA-256 mismatch for {filename}: "
                    f"expected {expected_sha256[:16]}..., got {actual[:16]}...")

        # Atomic rename (.tmp -> final)
        if os.path.exists(dest_path):
            os.unlink(dest_path)
        os.rename(tmp_path, dest_path)
        logger.info("Downloaded: %s (%d bytes)", filename, downloaded)
        return dest_path

    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        # Clean up temp file on failure
        if tmp_fd is not None:
            os.close(tmp_fd)
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        if isinstance(e, HubChecksumError):
            raise
        raise HubConnectionError(f"Download failed: {e}") from e
    except HubChecksumError:
        raise
    except Exception:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def resolve_download_order(hub_index, package_name, local_packages):
    """Determine dependency-first download order for a package.

    Resolves dependencies declared in the Hub index entry and returns
    a list of packages to download in order (dependencies first).
    Packages already present locally with the same or newer version are skipped.

    Args:
        hub_index: Parsed Hub index dict.
        package_name: Name of the package to download.
        local_packages: List of local package info dicts with 'name' keys.

    Returns:
        List of dicts, each with: name, version, entry (Hub version entry).
        Ordered dependency-first. Empty list if package not found in Hub.
    """
    hub_packages = hub_index.get("packages", {})
    local_map = {pkg["name"]: pkg.get("version", "") for pkg in local_packages}
    result = []
    visited = set()

    def _needs_download(name, hub_version):
        """Return True if the package should be downloaded."""
        if name not in local_map:
            return True
        local_ver = local_map[name]
        if not local_ver:
            return True
        try:
            return _parse_semver(hub_version) > _parse_semver(local_ver)
        except ValueError:
            return False

    def _resolve(name):
        if name in visited:
            return
        visited.add(name)

        if name not in hub_packages:
            return

        pkg_data = hub_packages[name]
        latest = pkg_data.get("latest", "")
        entry = pkg_data.get("versions", {}).get(latest, {})

        # Resolve dependencies first
        deps = entry.get("dependencies", {})
        for dep_name in deps:
            if _needs_download(dep_name, hub_packages.get(dep_name, {}).get("latest", "")):
                _resolve(dep_name)

        # Add this package if not local or outdated
        if _needs_download(name, latest):
            result.append({
                "name": name,
                "version": latest,
                "entry": entry,
            })

    _resolve(package_name)
    return result
