# SCODA Hub Manifest Specification

**Version:** 1.0
**Date:** 2026-02-25

---

## 1. Overview

SCODA Hub is a static registry for searching, downloading, and resolving dependencies of `.scoda` packages.
The Hub is composed of three JSON schemas:

| File | Location | Role |
|------|----------|------|
| **Hub Manifest** | Package repo Release asset | Distribution metadata for individual packages |
| **Hub Index** | scoda-engine GitHub Pages | Full package catalog (auto-generated) |
| **Sources** | `hub/sources.json` | List of repos to collect from (manually maintained) |

### Relationship with the internal .scoda manifest

The `manifest.json` inside a `.scoda` file describes the **package contents** (data structure, record count, data.db integrity).
The Hub Manifest describes the **package distribution** (download URL, .scoda file integrity, size).
These two serve different purposes. The core goal of the Hub Manifest is to provide package information without needing to open the `.scoda` file.

### Dual SHA-256 Structure

| Checksum | Target | Location | Purpose |
|----------|--------|----------|---------|
| `data_checksum_sha256` | `data.db` file | Internal .scoda manifest | Package data integrity |
| `sha256` | Entire `.scoda` file | Hub Manifest | Download integrity |

---

## 2. Hub Manifest (per-package)

A file uploaded to the GitHub Release of the package repo.

**Filename convention:** `{package_id}-{version}.manifest.json`

```json
{
  "hub_manifest_version": "1.0",
  "package_id": "trilobase",
  "version": "0.2.2",
  "title": "Trilobase - Genus-level trilobite taxonomy",
  "description": "Genus-level trilobite taxonomy database",
  "license": "CC-BY-4.0",
  "created_at": "2026-02-20T12:00:00Z",
  "provenance": ["Jell & Adrain 2002", "Adrain 2011"],
  "dependencies": {
    "paleocore": ">=0.1.3,<0.2.0"
  },
  "filename": "trilobase-0.2.2.scoda",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 524288,
  "scoda_format_version": "1.0",
  "engine_compat": ">=0.1.0"
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|:--------:|-------------|
| `hub_manifest_version` | string | Y | Hub Manifest schema version. Currently `"1.0"` |
| `package_id` | string | Y | Unique package identifier. Same as `name` inside the .scoda |
| `version` | string | Y | Package version. SemVer (`MAJOR.MINOR.PATCH`) |
| `title` | string | Y | Human-readable package title |
| `description` | string | Y | Package description |
| `license` | string | - | License identifier (SPDX). E.g., `"CC-BY-4.0"` |
| `created_at` | string | - | Package creation time. ISO 8601 format |
| `provenance` | string[] | - | List of data sources (references, etc.) |
| `dependencies` | object | - | Dependent packages. `{name: version_spec}` format |
| `filename` | string | - | `.scoda` filename. Default: `{package_id}-{version}.scoda`. Corresponds to the Hub Manifest filename |
| `sha256` | string | Y | SHA-256 hash of the `.scoda` file (hex digest) |
| `size_bytes` | integer | - | `.scoda` file size (bytes) |
| `scoda_format_version` | string | - | SCODA format version. Default: `"1.0"` |
| `engine_compat` | string | - | Compatible Engine version range. E.g., `">=0.1.0"` |

### dependencies Format

Keys are package names, values are SemVer version range strings:

```json
{
  "paleocore": ">=0.1.3,<0.2.0"
}
```

If there are no dependencies, use an empty object `{}` or omit the field.

### download_url Handling

The Hub Manifest does **not** include `download_url`.
This is because the GitHub Release URL is not finalized at build time.
The `download_url` is collected from the GitHub API by scoda-engine when generating the Hub Index.

---

## 3. Hub Index (`index.json`)

An auto-generated catalog hosted on scoda-engine GitHub Pages.

**URL:** `https://{user}.github.io/scoda-engine/index.json`

```json
{
  "hub_version": "1.0",
  "generated_at": "2026-02-24T15:00:00+00:00",
  "sources": [
    {"repo": "jikhanjung/trilobase", "type": "github_releases"}
  ],
  "packages": {
    "trilobase": {
      "latest": "0.2.2",
      "versions": {
        "0.2.2": {
          "title": "Trilobase - Genus-level trilobite taxonomy",
          "description": "Genus-level trilobite taxonomy database",
          "download_url": "https://github.com/jikhanjung/trilobase/releases/download/v0.2.2/trilobase-0.2.2.scoda",
          "sha256": "e3b0c44...",
          "size_bytes": 524288,
          "dependencies": {"paleocore": ">=0.1.3,<0.2.0"},
          "engine_compat": ">=0.1.0",
          "scoda_format_version": "1.0",
          "license": "CC-BY-4.0",
          "created_at": "2026-02-20T12:00:00Z",
          "source_release": "https://github.com/jikhanjung/trilobase/releases/tag/v0.2.2"
        }
      }
    }
  }
}
```

### Root Fields

| Field | Type | Description |
|-------|------|-------------|
| `hub_version` | string | Hub Index schema version. Currently `"1.0"` |
| `generated_at` | string | Index generation time. ISO 8601 format |
| `sources` | object[] | List of repos to collect from |
| `packages` | object | Package catalog. Key: package_id |

### packages.{package_id}

| Field | Type | Description |
|-------|------|-------------|
| `latest` | string | Latest version string (sorted by SemVer) |
| `versions` | object | Per-version entries. Key: version string |

### packages.{package_id}.versions.{version} (Version Entry)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Package title |
| `description` | string | Package description |
| `download_url` | string | `.scoda` file download URL |
| `sha256` | string | `.scoda` file SHA-256 hash |
| `size_bytes` | integer | `.scoda` file size (bytes) |
| `dependencies` | object | Dependent packages `{name: version_spec}` |
| `engine_compat` | string | Compatible Engine version range |
| `scoda_format_version` | string | SCODA format version |
| `license` | string | License identifier |
| `created_at` | string | Package creation time |
| `source_release` | string | GitHub Release page URL |

### Collection Strategy and the Role of Hub Manifest

The index generation script (`generate_hub_index.py`) operates with two strategies.
Hub Manifest is **optional** -- basic package discovery and download work even without it.

#### Strategy 1: Hub Manifest Parsing (when manifest is present)

If a release has a `*.manifest.json` asset, it is downloaded and parsed.
All metadata fields are populated, and SHA-256 verification and dependency resolution work fully.

#### Strategy 2: Fallback (when manifest is absent)

If a release has no `*.manifest.json`, metadata is inferred from the `.scoda` filename.
The package_id and version are extracted from the filename pattern `{package_id}-{version}.scoda` (e.g., `trilobase-0.2.2.scoda`),
and `download_url` and `size_bytes` are collected from the GitHub API.

#### Data Comparison by Strategy

| Field | Strategy 1 (manifest) | Strategy 2 (fallback) |
|-------|:---------------------:|:---------------------:|
| `download_url` | Y | Y |
| `size_bytes` | Y | Y |
| `title` | Actual title | package_id as-is |
| `description` | Y | Empty string |
| `sha256` | Y | Empty string |
| `dependencies` | Y | `{}` |
| `license` | Y | Empty string |
| `engine_compat` | Y | Empty string |
| `created_at` | Manifest value | Release published_at |

#### Limitations of Fallback

The following features **do not work** in fallback mode:

- **SHA-256 verification**: Since `sha256` is an empty string, download integrity verification is not possible
- **Automatic dependency resolution**: Since `dependencies` is an empty object, `resolve_download_order()` cannot recognize dependent packages. For example, even if trilobase depends on paleocore, only trilobase is downloaded and paleocore is not automatically fetched
- **Metadata display**: Title, description, license, etc. are not displayed, resulting in a degraded user experience

Therefore, fallback is intended for **quick-start purposes only**, and it is recommended to upload the Hub Manifest alongside production releases.

---

## 4. Sources (`hub/sources.json`)

List of repos to collect from. Manually maintained and committed to git.

```json
[
  {
    "repo": "jikhanjung/trilobase",
    "type": "github_releases"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `repo` | string | GitHub repo (`owner/repo` format) |
| `type` | string | Source type. Currently only `"github_releases"` is supported |

---

## 5. Collection Workflow

```
Package repo (trilobase)                 scoda-engine repo
┌──────────────────────────┐             ┌───────────────────────────┐
│  GitHub Release          │  read-only  │  hub/sources.json         │
│  ├── *.scoda             │◄────────────│  scripts/generate_hub_   │
│  └── *.manifest.json     │  GitHub API │    index.py               │
└──────────────────────────┘             │  → hub/index.json         │
                                         │  → Deploy to GitHub Pages │
                                         └───────────────────────────┘
```

### Processing Order

1. Read the list of target repos from `hub/sources.json`
2. Query each repo's releases via the GitHub REST API
3. If a `*.manifest.json` asset exists, parse it (Strategy 1)
4. Otherwise, infer from the `.scoda` filename (Strategy 2 -- Fallback)
5. Collect `download_url` from the GitHub API's `browser_download_url`
6. Merge by version to generate `index.json`
7. Deploy to the `gh-pages` branch

### Triggers

- `workflow_dispatch` (manual execution)
- `schedule` (daily cron)

### Scripts

```bash
# Generate
python scripts/generate_hub_index.py

# dry-run (output to stdout, no file created)
python scripts/generate_hub_index.py --dry-run

# Include all versions (default is latest only)
python scripts/generate_hub_index.py --all
```

---

## 6. Client Behavior

Actions performed by the Hub client (`scoda_engine_core.hub_client`):

### Index Retrieval

```python
from scoda_engine_core.hub_client import fetch_hub_index

index = fetch_hub_index()  # Uses SCODA_HUB_URL environment variable or default URL
```

### Local Comparison

```python
from scoda_engine_core.hub_client import compare_with_local

result = compare_with_local(index, local_packages)
# result["available"]   — packages not installed locally
# result["updatable"]   — packages with available updates
# result["up_to_date"]  — packages already at the latest version
```

### Dependency Resolution and Download

```python
from scoda_engine_core.hub_client import resolve_download_order, download_package

order = resolve_download_order(index, "trilobase", local_packages)
# → [{"name": "paleocore", ...}, {"name": "trilobase", ...}]  (dependencies first)

for pkg in order:
    path = download_package(
        pkg["entry"]["download_url"],
        dest_dir="/path/to/packages",
        expected_sha256=pkg["entry"].get("sha256"),
    )
```

### SHA-256 Verification

If `expected_sha256` is provided during download, it is automatically verified.
On mismatch, a `HubChecksumError` is raised and the temporary file is automatically deleted.

---

## 7. Hub Manifest Generation Guide (for Package Builders)

Generate the Hub Manifest alongside the `.scoda` file immediately after building the package.

```python
import hashlib, json, os

def generate_hub_manifest(scoda_path, package_id, version, title,
                          description="", license="", dependencies=None,
                          provenance=None, scoda_format_version="1.0",
                          engine_compat=""):
    """Generate a Hub manifest JSON file alongside the .scoda file."""
    # SHA-256 of .scoda file
    sha256 = hashlib.sha256()
    with open(scoda_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    manifest = {
        "hub_manifest_version": "1.0",
        "package_id": package_id,
        "version": version,
        "title": title,
        "description": description,
        "license": license,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance or [],
        "dependencies": dependencies or {},
        "filename": os.path.basename(scoda_path),
        "sha256": sha256.hexdigest(),
        "size_bytes": os.path.getsize(scoda_path),
        "scoda_format_version": scoda_format_version,
        "engine_compat": engine_compat,
    }

    out_dir = os.path.dirname(scoda_path)
    manifest_path = os.path.join(out_dir, f"{package_id}-{version}.manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return manifest_path
```

### GitHub Release Upload

```yaml
# release.yml
- name: Upload release assets
  run: |
    gh release upload ${{ github.ref_name }} \
      dist/*.scoda \
      dist/*.manifest.json
```

---

## 8. Future Extensions (Reserved Fields)

Fields not currently used but may be added in future versions:

| Field | Description |
|-------|-------------|
| `deprecated` | boolean -- Whether the package is deprecated |
| `replaced_by` | string -- Replacement package ID |
| `signature` | string -- Package signature (code signing) |
| `tags` | string[] -- Tags for search |
| `homepage` | string -- Project homepage URL |

---

## 9. References

- Design document: `devlog/20260224_P15_scoda_hub_static_registry.md`
- Index generation script: `scripts/generate_hub_index.py`
- Hub client: `core/scoda_engine_core/hub_client.py`
- Internal .scoda manifest spec: `docs/SCODA_WHITEPAPER.md` Section 2.2
