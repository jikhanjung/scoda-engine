"""
Tests for scoda_engine_core.hub_client — Hub client pure-function tests.

Uses unittest.mock to avoid real network calls.
"""

import hashlib
import json
import os
import urllib.error
import urllib.request
from unittest import mock

import pytest

from scoda_engine_core.hub_client import (
    HubChecksumError,
    HubConnectionError,
    HubError,
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
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_hub_error_hierarchy(self):
        assert issubclass(HubConnectionError, HubError)
        assert issubclass(HubChecksumError, HubError)
        assert issubclass(HubError, Exception)
