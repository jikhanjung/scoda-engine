"""
Tests for scoda_engine_core.hub_client — Hub client pure-function tests.

Uses unittest.mock to avoid real network calls.
"""

import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from unittest import mock

import pytest

from scoda_engine_core.hub_client import (
    HubChecksumError,
    HubConnectionError,
    HubError,
    HubSSLError,
    _create_ssl_context,
    _is_ssl_error,
    _load_windows_store_certs,
    compare_with_local,
    download_package,
    fetch_hub_index,
    resolve_download_order,
)


# ---------------------------------------------------------------------------
# Sample Hub index for testing
# ---------------------------------------------------------------------------

def _make_hub_index(packages=None):
    """Build a minimal Hub index dict."""
    return {
        "hub_version": "1.0",
        "generated_at": "2026-02-24T00:00:00+00:00",
        "sources": [],
        "packages": packages or {},
    }


def _make_pkg_entry(version="1.0.0", download_url="https://example.com/pkg-1.0.0.scoda",
                    sha256="", size_bytes=1024, dependencies=None):
    return {
        "title": "Test Package",
        "description": "A test package",
        "download_url": download_url,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "dependencies": dependencies or {},
        "engine_compat": "",
        "scoda_format_version": "1.0",
        "license": "MIT",
        "created_at": "2026-02-24T00:00:00+00:00",
        "source_release": "https://github.com/test/repo/releases/tag/v1.0.0",
    }


# ---------------------------------------------------------------------------
# compare_with_local tests
# ---------------------------------------------------------------------------

class TestCompareWithLocal:
    def test_available_package(self):
        """Hub-only package shows up as available."""
        index = _make_hub_index({
            "alpha": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            }
        })
        result = compare_with_local(index, [])
        assert len(result["available"]) == 1
        assert result["available"][0]["name"] == "alpha"
        assert result["available"][0]["hub_version"] == "1.0.0"
        assert result["updatable"] == []
        assert result["up_to_date"] == []

    def test_updatable_package(self):
        """Local package with older version shows up as updatable."""
        index = _make_hub_index({
            "beta": {
                "latest": "2.0.0",
                "versions": {"2.0.0": _make_pkg_entry("2.0.0")},
            }
        })
        local = [{"name": "beta", "version": "1.0.0"}]
        result = compare_with_local(index, local)
        assert len(result["updatable"]) == 1
        assert result["updatable"][0]["name"] == "beta"
        assert result["updatable"][0]["hub_version"] == "2.0.0"
        assert result["updatable"][0]["local_version"] == "1.0.0"
        assert result["available"] == []
        assert result["up_to_date"] == []

    def test_up_to_date_package(self):
        """Same version is up_to_date."""
        index = _make_hub_index({
            "gamma": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            }
        })
        local = [{"name": "gamma", "version": "1.0.0"}]
        result = compare_with_local(index, local)
        assert len(result["up_to_date"]) == 1
        assert result["up_to_date"][0]["name"] == "gamma"
        assert result["available"] == []
        assert result["updatable"] == []

    def test_local_newer_than_hub(self):
        """Local version newer than Hub is treated as up_to_date."""
        index = _make_hub_index({
            "delta": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            }
        })
        local = [{"name": "delta", "version": "2.0.0"}]
        result = compare_with_local(index, local)
        assert len(result["up_to_date"]) == 1
        assert result["available"] == []
        assert result["updatable"] == []

    def test_mixed_packages(self):
        """Multiple packages with different statuses."""
        index = _make_hub_index({
            "new-pkg": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            },
            "old-pkg": {
                "latest": "3.0.0",
                "versions": {"3.0.0": _make_pkg_entry("3.0.0")},
            },
            "same-pkg": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            },
        })
        local = [
            {"name": "old-pkg", "version": "1.0.0"},
            {"name": "same-pkg", "version": "1.0.0"},
        ]
        result = compare_with_local(index, local)
        assert len(result["available"]) == 1
        assert result["available"][0]["name"] == "new-pkg"
        assert len(result["updatable"]) == 1
        assert result["updatable"][0]["name"] == "old-pkg"
        assert len(result["up_to_date"]) == 1
        assert result["up_to_date"][0]["name"] == "same-pkg"

    def test_empty_hub(self):
        """Empty Hub index returns all empty lists."""
        result = compare_with_local(_make_hub_index({}), [])
        assert result == {"available": [], "updatable": [], "up_to_date": []}

    def test_no_download_url_skipped(self):
        """Packages without download_url are skipped."""
        entry = _make_pkg_entry()
        entry["download_url"] = ""
        index = _make_hub_index({
            "no-url": {"latest": "1.0.0", "versions": {"1.0.0": entry}},
        })
        result = compare_with_local(index, [])
        assert result["available"] == []

    def test_semver_comparison_patch(self):
        """Patch version difference detected."""
        index = _make_hub_index({
            "pkg": {
                "latest": "1.0.1",
                "versions": {"1.0.1": _make_pkg_entry("1.0.1")},
            }
        })
        local = [{"name": "pkg", "version": "1.0.0"}]
        result = compare_with_local(index, local)
        assert len(result["updatable"]) == 1


# ---------------------------------------------------------------------------
# resolve_download_order tests
# ---------------------------------------------------------------------------

class TestResolveDownloadOrder:
    def test_single_package_no_deps(self):
        """Package with no dependencies returns just itself."""
        index = _make_hub_index({
            "alpha": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry("1.0.0")},
            }
        })
        order = resolve_download_order(index, "alpha", [])
        assert len(order) == 1
        assert order[0]["name"] == "alpha"

    def test_package_with_dep(self):
        """Package with a dependency returns dep first."""
        dep_entry = _make_pkg_entry("1.0.0",
                                    download_url="https://example.com/dep-1.0.0.scoda")
        main_entry = _make_pkg_entry("2.0.0",
                                     download_url="https://example.com/main-2.0.0.scoda",
                                     dependencies={"dep": ">=1.0.0"})
        index = _make_hub_index({
            "main": {"latest": "2.0.0", "versions": {"2.0.0": main_entry}},
            "dep": {"latest": "1.0.0", "versions": {"1.0.0": dep_entry}},
        })
        order = resolve_download_order(index, "main", [])
        assert len(order) == 2
        assert order[0]["name"] == "dep"
        assert order[1]["name"] == "main"

    def test_dep_already_local(self):
        """Dependency already installed locally is skipped."""
        main_entry = _make_pkg_entry(dependencies={"dep": ">=1.0.0"})
        dep_entry = _make_pkg_entry()
        index = _make_hub_index({
            "main": {"latest": "1.0.0", "versions": {"1.0.0": main_entry}},
            "dep": {"latest": "1.0.0", "versions": {"1.0.0": dep_entry}},
        })
        local = [{"name": "dep", "version": "1.0.0"}]
        order = resolve_download_order(index, "main", local)
        assert len(order) == 1
        assert order[0]["name"] == "main"

    def test_package_already_local(self):
        """Package already installed locally returns empty list."""
        index = _make_hub_index({
            "alpha": {
                "latest": "1.0.0",
                "versions": {"1.0.0": _make_pkg_entry()},
            }
        })
        local = [{"name": "alpha", "version": "1.0.0"}]
        order = resolve_download_order(index, "alpha", local)
        assert order == []

    def test_package_not_in_hub(self):
        """Package not in Hub returns empty list."""
        index = _make_hub_index({})
        order = resolve_download_order(index, "missing", [])
        assert order == []

    def test_dep_not_in_hub(self):
        """Missing dependency in Hub is skipped (only main downloaded)."""
        main_entry = _make_pkg_entry(dependencies={"missing-dep": ">=1.0.0"})
        index = _make_hub_index({
            "main": {"latest": "1.0.0", "versions": {"1.0.0": main_entry}},
        })
        order = resolve_download_order(index, "main", [])
        assert len(order) == 1
        assert order[0]["name"] == "main"

    def test_circular_deps(self):
        """Circular dependencies don't cause infinite loop."""
        entry_a = _make_pkg_entry(dependencies={"b": ""})
        entry_b = _make_pkg_entry(dependencies={"a": ""})
        index = _make_hub_index({
            "a": {"latest": "1.0.0", "versions": {"1.0.0": entry_a}},
            "b": {"latest": "1.0.0", "versions": {"1.0.0": entry_b}},
        })
        order = resolve_download_order(index, "a", [])
        names = [o["name"] for o in order]
        assert "a" in names
        assert "b" in names
        assert len(names) == 2


# ---------------------------------------------------------------------------
# fetch_hub_index tests (mocked network)
# ---------------------------------------------------------------------------

class TestFetchHubIndex:
    def test_fetch_success(self):
        """Successful fetch returns parsed JSON."""
        index_data = _make_hub_index({"test": {"latest": "1.0.0", "versions": {}}})
        body = json.dumps(index_data).encode("utf-8")

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            result = fetch_hub_index(hub_url="https://example.com/index.json")

        assert result["hub_version"] == "1.0"
        assert "test" in result["packages"]

    def test_fetch_network_error(self):
        """Network error raises HubConnectionError."""
        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("timeout")):
            with pytest.raises(HubConnectionError, match="Failed to fetch"):
                fetch_hub_index(hub_url="https://example.com/index.json")

    def test_fetch_ssl_error_raises_hub_ssl_error(self):
        """SSL error raises HubSSLError (subclass of HubConnectionError)."""
        ssl_exc = urllib.error.URLError(
            ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=ssl_exc):
            with pytest.raises(HubSSLError, match="SSL certificate"):
                fetch_hub_index(hub_url="https://example.com/index.json")

    def test_fetch_ssl_noverify_skips_verification(self):
        """ssl_noverify=True uses noverify context."""
        index_data = _make_hub_index({})
        body = json.dumps(index_data).encode("utf-8")

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        captured = []
        def capture_urlopen(req, **kwargs):
            captured.append(kwargs.get("context"))
            return mock_resp

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=capture_urlopen):
            fetch_hub_index(hub_url="https://example.com/index.json",
                            ssl_noverify=True)

        ctx = captured[0]
        assert ctx is not None
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_fetch_invalid_json(self):
        """Invalid JSON raises HubConnectionError."""
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            with pytest.raises(HubConnectionError, match="Invalid Hub index"):
                fetch_hub_index(hub_url="https://example.com/index.json")

    def test_fetch_uses_env_var(self):
        """SCODA_HUB_URL environment variable is used when no URL provided."""
        index_data = _make_hub_index({})
        body = json.dumps(index_data).encode("utf-8")

        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = body
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        captured_req = []

        def capture_urlopen(req, **kwargs):
            captured_req.append(req)
            return mock_resp

        with mock.patch.dict(os.environ, {"SCODA_HUB_URL": "https://custom.hub/index.json"}):
            with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                            side_effect=capture_urlopen):
                fetch_hub_index()

        assert captured_req[0].full_url == "https://custom.hub/index.json"


# ---------------------------------------------------------------------------
# download_package tests (mocked network)
# ---------------------------------------------------------------------------

class TestDownloadPackage:
    def test_download_success(self, tmp_path):
        """Successful download creates file with correct content."""
        content = b"fake scoda package content"
        sha256 = hashlib.sha256(content).hexdigest()

        mock_resp = mock.MagicMock()
        mock_resp.read = mock.MagicMock(side_effect=[content, b""])
        mock_resp.headers = {"Content-Length": str(len(content))}
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            path = download_package(
                "https://example.com/test-1.0.0.scoda",
                str(tmp_path),
                expected_sha256=sha256,
            )

        assert os.path.exists(path)
        assert path.endswith("test-1.0.0.scoda")
        with open(path, "rb") as f:
            assert f.read() == content

    def test_download_checksum_mismatch(self, tmp_path):
        """SHA-256 mismatch raises HubChecksumError and cleans up."""
        content = b"fake content"

        mock_resp = mock.MagicMock()
        mock_resp.read = mock.MagicMock(side_effect=[content, b""])
        mock_resp.headers = {"Content-Length": str(len(content))}
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            with pytest.raises(HubChecksumError, match="SHA-256 mismatch"):
                download_package(
                    "https://example.com/bad-1.0.0.scoda",
                    str(tmp_path),
                    expected_sha256="0000000000000000000000000000000000000000000000000000000000000000",
                )

        # No .scoda or .tmp files should remain
        remaining = [f for f in os.listdir(str(tmp_path))
                     if f.endswith(".scoda") or f.endswith(".tmp")]
        assert remaining == []

    def test_download_network_error(self, tmp_path):
        """Network error raises HubConnectionError and cleans up."""
        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("connection refused")):
            with pytest.raises(HubConnectionError, match="Download failed"):
                download_package(
                    "https://example.com/fail-1.0.0.scoda",
                    str(tmp_path),
                )

        remaining = [f for f in os.listdir(str(tmp_path)) if f.endswith(".tmp")]
        assert remaining == []

    def test_download_ssl_error_raises_hub_ssl_error(self, tmp_path):
        """SSL error during download raises HubSSLError."""
        ssl_exc = urllib.error.URLError(
            ssl.SSLCertVerificationError("CERTIFICATE_VERIFY_FAILED"))
        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=ssl_exc):
            with pytest.raises(HubSSLError, match="SSL certificate"):
                download_package(
                    "https://example.com/ssl-fail-1.0.0.scoda",
                    str(tmp_path),
                )

    def test_download_ssl_noverify(self, tmp_path):
        """ssl_noverify=True downloads without SSL verification."""
        content = b"noverify content"
        sha256 = hashlib.sha256(content).hexdigest()

        mock_resp = mock.MagicMock()
        mock_resp.read = mock.MagicMock(side_effect=[content, b""])
        mock_resp.headers = {"Content-Length": str(len(content))}
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        captured = []
        def capture_urlopen(req, **kwargs):
            captured.append(kwargs.get("context"))
            return mock_resp

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        side_effect=capture_urlopen):
            path = download_package(
                "https://example.com/nv-1.0.0.scoda",
                str(tmp_path),
                expected_sha256=sha256,
                ssl_noverify=True,
            )

        assert os.path.exists(path)
        ctx = captured[0]
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_download_progress_callback(self, tmp_path):
        """Progress callback is called during download."""
        content = b"x" * 100

        mock_resp = mock.MagicMock()
        mock_resp.read = mock.MagicMock(side_effect=[content, b""])
        mock_resp.headers = {"Content-Length": str(len(content))}
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        progress_calls = []

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            download_package(
                "https://example.com/prog-1.0.0.scoda",
                str(tmp_path),
                progress_callback=lambda dl, total: progress_calls.append((dl, total)),
            )

        assert len(progress_calls) >= 1
        assert progress_calls[-1][0] == 100  # downloaded bytes
        assert progress_calls[-1][1] == 100  # total bytes

    def test_download_no_sha256(self, tmp_path):
        """Download without SHA-256 check succeeds."""
        content = b"no checksum content"

        mock_resp = mock.MagicMock()
        mock_resp.read = mock.MagicMock(side_effect=[content, b""])
        mock_resp.headers = {"Content-Length": str(len(content))}
        mock_resp.__enter__ = mock.MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = mock.MagicMock(return_value=False)

        with mock.patch("scoda_engine_core.hub_client.urllib.request.urlopen",
                        return_value=mock_resp):
            path = download_package(
                "https://example.com/nochk-1.0.0.scoda",
                str(tmp_path),
            )

        assert os.path.exists(path)


# ---------------------------------------------------------------------------
# _create_ssl_context tests
# ---------------------------------------------------------------------------

class TestCreateSslContext:
    def test_default_non_windows(self):
        """Default (no env vars, non-Windows) returns None."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("scoda_engine_core.hub_client.sys") as mock_sys:
                mock_sys.platform = "linux"
                ctx = _create_ssl_context()
        assert ctx is None

    def test_default_windows_loads_store(self):
        """Default on Windows returns context with system certs loaded."""
        mock_ctx = mock.MagicMock(spec=ssl.SSLContext)
        with mock.patch.dict(os.environ, {}, clear=True):
            with mock.patch("scoda_engine_core.hub_client.sys") as mock_sys:
                mock_sys.platform = "win32"
                with mock.patch("scoda_engine_core.hub_client.ssl.create_default_context",
                                return_value=mock_ctx):
                    with mock.patch("scoda_engine_core.hub_client._load_windows_store_certs",
                                    return_value=5) as mock_load:
                        ctx = _create_ssl_context()
        assert ctx is mock_ctx
        mock_load.assert_called_once_with(mock_ctx)

    def test_ssl_verify_disabled(self):
        """SCODA_HUB_SSL_VERIFY=0 returns a context with verification off."""
        with mock.patch.dict(os.environ, {"SCODA_HUB_SSL_VERIFY": "0"}):
            ctx = _create_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    def test_ssl_verify_enabled_explicitly(self):
        """SCODA_HUB_SSL_VERIFY=1 on non-Windows returns None."""
        with mock.patch.dict(os.environ, {"SCODA_HUB_SSL_VERIFY": "1"}):
            with mock.patch("scoda_engine_core.hub_client.sys") as mock_sys:
                mock_sys.platform = "linux"
                ctx = _create_ssl_context()
        assert ctx is None

    def test_ssl_cert_valid_file(self, tmp_path):
        """SCODA_HUB_SSL_CERT with valid file returns context with custom CA."""
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("-----BEGIN CERTIFICATE-----\nMIIB...\n-----END CERTIFICATE-----\n")

        with mock.patch.dict(os.environ, {"SCODA_HUB_SSL_CERT": str(ca_file)}):
            with mock.patch("scoda_engine_core.hub_client.ssl.create_default_context") as mock_ctx:
                mock_ctx.return_value = mock.MagicMock(spec=ssl.SSLContext)
                ctx = _create_ssl_context()

        mock_ctx.assert_called_once_with(cafile=str(ca_file))
        assert ctx is not None

    def test_ssl_cert_missing_file(self, tmp_path):
        """SCODA_HUB_SSL_CERT with non-existent file returns None."""
        with mock.patch.dict(os.environ,
                             {"SCODA_HUB_SSL_CERT": str(tmp_path / "nope.pem")}):
            ctx = _create_ssl_context()
        assert ctx is None

    def test_ssl_verify_takes_precedence(self, tmp_path):
        """SCODA_HUB_SSL_VERIFY=0 takes precedence over SCODA_HUB_SSL_CERT."""
        ca_file = tmp_path / "ca.pem"
        ca_file.write_text("dummy")
        with mock.patch.dict(os.environ, {
            "SCODA_HUB_SSL_VERIFY": "0",
            "SCODA_HUB_SSL_CERT": str(ca_file),
        }):
            ctx = _create_ssl_context()
        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.verify_mode == ssl.CERT_NONE


class TestLoadWindowsStoreCerts:
    """Tests for _load_windows_store_certs.

    ssl.enum_certificates is Windows-only, so we use create=True
    to allow mocking it on Linux CI environments.
    """

    def test_loads_certs_from_root_and_ca_stores(self):
        """Loads DER certs from ROOT and CA stores, converts to PEM."""
        fake_der = b"\x30\x82\x01\x00"
        fake_pem = "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n"

        mock_ctx = mock.MagicMock(spec=ssl.SSLContext)

        def fake_enum(store_name):
            return [(fake_der, "x509_asn", True)]

        with mock.patch("scoda_engine_core.hub_client.ssl.enum_certificates",
                        side_effect=fake_enum, create=True):
            with mock.patch("scoda_engine_core.hub_client.ssl.DER_cert_to_PEM_cert",
                            return_value=fake_pem):
                loaded = _load_windows_store_certs(mock_ctx)

        assert loaded == 2  # one from ROOT + one from CA
        assert mock_ctx.load_verify_locations.call_count == 2

    def test_skips_non_x509_encodings(self):
        """Non-x509_asn encodings are skipped."""
        mock_ctx = mock.MagicMock(spec=ssl.SSLContext)

        def fake_enum(store_name):
            return [(b"data", "pkcs_7_asn", True)]

        with mock.patch("scoda_engine_core.hub_client.ssl.enum_certificates",
                        side_effect=fake_enum, create=True):
            loaded = _load_windows_store_certs(mock_ctx)

        assert loaded == 0
        mock_ctx.load_verify_locations.assert_not_called()

    def test_handles_ssl_error_gracefully(self):
        """SSLError on individual cert load is skipped, others continue."""
        fake_pem = "-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n"
        mock_ctx = mock.MagicMock(spec=ssl.SSLContext)
        mock_ctx.load_verify_locations.side_effect = ssl.SSLError("bad cert")

        def fake_enum(store_name):
            return [(b"\x30", "x509_asn", True)]

        with mock.patch("scoda_engine_core.hub_client.ssl.enum_certificates",
                        side_effect=fake_enum, create=True):
            with mock.patch("scoda_engine_core.hub_client.ssl.DER_cert_to_PEM_cert",
                            return_value=fake_pem):
                loaded = _load_windows_store_certs(mock_ctx)

        assert loaded == 0  # all failed

    def test_handles_os_error_on_store_access(self):
        """OSError when accessing a store is handled gracefully."""
        mock_ctx = mock.MagicMock(spec=ssl.SSLContext)

        with mock.patch("scoda_engine_core.hub_client.ssl.enum_certificates",
                        side_effect=OSError("access denied"), create=True):
            loaded = _load_windows_store_certs(mock_ctx)

        assert loaded == 0


# ---------------------------------------------------------------------------
# _is_ssl_error tests
# ---------------------------------------------------------------------------

class TestIsSslError:
    def test_ssl_cert_verification_error(self):
        exc = ssl.SSLCertVerificationError("cert verify failed")
        assert _is_ssl_error(exc) is True

    def test_ssl_error(self):
        exc = ssl.SSLError("ssl handshake failed")
        assert _is_ssl_error(exc) is True

    def test_url_error_wrapping_ssl(self):
        reason = ssl.SSLCertVerificationError("cert verify failed")
        exc = urllib.error.URLError(reason)
        assert _is_ssl_error(exc) is True

    def test_url_error_non_ssl(self):
        exc = urllib.error.URLError("connection refused")
        assert _is_ssl_error(exc) is False

    def test_non_ssl_exception(self):
        exc = OSError("disk full")
        assert _is_ssl_error(exc) is False


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_hub_error_hierarchy(self):
        assert issubclass(HubConnectionError, HubError)
        assert issubclass(HubSSLError, HubConnectionError)
        assert issubclass(HubChecksumError, HubError)
        assert issubclass(HubError, Exception)

    def test_hub_ssl_error_caught_as_connection_error(self):
        """HubSSLError can be caught as HubConnectionError."""
        with pytest.raises(HubConnectionError):
            raise HubSSLError("ssl failed")
