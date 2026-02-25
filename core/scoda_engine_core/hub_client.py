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
import ssl
import sys
import tempfile
import urllib.error
import urllib.request

from .scoda_package import _parse_semver

logger = logging.getLogger(__name__)

DEFAULT_HUB_URL = "https://jikhanjung.github.io/scoda-engine/index.json"


def _load_windows_store_certs(ctx):
    """Load certificates from the Windows system certificate store.

    Browsers (Chrome, Edge) use the Windows certificate store which
    includes corporate/proxy CA certificates installed by IT.
    Python's bundled CA certificates do NOT include these, causing
    HTTPS failures even when the same URLs work fine in browsers.

    This function bridges that gap by loading Windows store certs
    into the given SSL context via ssl.enum_certificates().

    Returns:
        Number of certificates loaded.
    """
    certs_loaded = 0
    for store_name in ("ROOT", "CA"):
        try:
            for cert, encoding, trust in ssl.enum_certificates(store_name):
                if encoding == "x509_asn":
                    try:
                        pem = ssl.DER_cert_to_PEM_cert(cert)
                        ctx.load_verify_locations(cadata=pem)
                        certs_loaded += 1
                    except ssl.SSLError:
                        pass
        except OSError:
            pass
    return certs_loaded


def _create_ssl_context():
    """Create an SSL context for Hub HTTPS requests.

    Supports the following environment variables:
      - SCODA_HUB_SSL_CERT: Path to a custom CA certificate bundle (PEM).
            Useful when behind a corporate SSL inspection proxy.
      - SCODA_HUB_SSL_VERIFY: Set to "0" to disable SSL certificate
            verification entirely (NOT recommended for production).

    On Windows, automatically loads the Windows system certificate store
    so that corporate/proxy CA certificates are available to Python,
    matching browser behavior.

    Returns:
        ssl.SSLContext or None (None = use urllib defaults).
    """
    ssl_verify = os.environ.get("SCODA_HUB_SSL_VERIFY", "1").strip()
    ssl_cert = os.environ.get("SCODA_HUB_SSL_CERT", "").strip()

    if ssl_verify == "0":
        logger.warning(
            "SSL certificate verification disabled (SCODA_HUB_SSL_VERIFY=0). "
            "This is insecure and should only be used for troubleshooting."
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if ssl_cert:
        if not os.path.isfile(ssl_cert):
            logger.warning("SCODA_HUB_SSL_CERT file not found: %s", ssl_cert)
            return None
        logger.info("Using custom CA bundle: %s", ssl_cert)
        ctx = ssl.create_default_context(cafile=ssl_cert)
        return ctx

    # On Windows, explicitly load the Windows certificate store.
    # Python's urllib uses its own bundled CA certs which do NOT include
    # corporate/proxy CA certificates that browsers (Chrome, Edge) trust
    # via the Windows store.  This is especially problematic with
    # PyInstaller builds where the cert bundle may be incomplete.
    if sys.platform == "win32":
        ctx = ssl.create_default_context()
        loaded = _load_windows_store_certs(ctx)
        if loaded:
            logger.debug(
                "Loaded %d certificate(s) from Windows system store", loaded
            )
        return ctx

    return None


def _create_noverify_ssl_context():
    """Create an SSL context that skips certificate verification.

    Package integrity is still guaranteed by SHA-256 checksum
    verification after download.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _is_ssl_error(exc):
    """Check whether an exception is caused by SSL certificate verification."""
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, ssl.SSLError):
        return True
    # urllib wraps SSL errors in URLError
    if isinstance(exc, urllib.error.URLError):
        return isinstance(getattr(exc, "reason", None),
                          (ssl.SSLError, ssl.SSLCertVerificationError))
    return False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class HubError(Exception):
    """Base exception for Hub operations."""


class HubConnectionError(HubError):
    """Raised when the Hub index cannot be fetched."""


class HubSSLError(HubConnectionError):
    """Raised when an SSL certificate verification error occurs.

    The GUI layer can catch this specifically to offer the user
    the option to retry without SSL verification.
    """


class HubChecksumError(HubError):
    """Raised when a downloaded file's SHA-256 does not match."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_hub_index(hub_url=None, timeout=10, ssl_noverify=False):
    """Fetch and parse the Hub index.json.

    Args:
        hub_url: URL to index.json. Defaults to SCODA_HUB_URL env var
                 or the hardcoded default.
        timeout: HTTP request timeout in seconds.
        ssl_noverify: If True, skip SSL certificate verification.

    Returns:
        Parsed index dict.

    Raises:
        HubSSLError: On SSL certificate verification failure.
        HubConnectionError: On other network or parse failure.
    """
    url = hub_url or os.environ.get("SCODA_HUB_URL") or DEFAULT_HUB_URL
    logger.info("Fetching Hub index from %s", url)

    req = urllib.request.Request(url, headers={
        "User-Agent": "ScodaDesktop",
        "Accept": "application/json",
    })
    if ssl_noverify:
        ssl_ctx = _create_noverify_ssl_context()
        logger.debug("SSL verification disabled for Hub index fetch")
    else:
        ssl_ctx = _create_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl_ctx) as resp:
            data = resp.read().decode("utf-8")
        index = json.loads(data)
        pkg_count = len(index.get("packages", {}))
        logger.info("Hub index fetched: %d package(s)", pkg_count)
        return index
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        if _is_ssl_error(e):
            raise HubSSLError(f"SSL certificate verification failed: {e}") from e
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
                     progress_callback=None, timeout=60, ssl_noverify=False):
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
        ssl_noverify: If True, skip SSL certificate verification.

    Returns:
        Path to the downloaded .scoda file.

    Raises:
        HubSSLError: On SSL certificate verification failure.
        HubConnectionError: On other network failure.
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
    if ssl_noverify:
        ssl_ctx = _create_noverify_ssl_context()
        logger.debug("SSL verification disabled for download")
    else:
        ssl_ctx = _create_ssl_context()

    # Use a named temp file in the same directory for atomic rename
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dest_dir)
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=ssl_ctx) as resp:
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
        if _is_ssl_error(e):
            raise HubSSLError(
                f"SSL certificate verification failed: {e}") from e
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
