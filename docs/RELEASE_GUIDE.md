# SCODA Desktop Release Guide

This document describes the full process of **data modification → .scoda package creation → release → distribution** for SCODA Desktop.

Following the SCODA (Self-Contained Data Artifact) principle, each release is **immutable** and identified by a version number.

---

## Table of Contents

1. [Version Number Rules](#version-number-rules)
2. [Release Procedure](#release-procedure)
3. [Distribution Procedure](#distribution-procedure)
4. [Overlay DB Compatibility](#overlay-db-compatibility)
5. [Verification and Testing](#verification-and-testing)
6. [Cautions](#cautions)

---

## Version Number Rules

**Semantic Versioning** format: `MAJOR.MINOR.PATCH`

| Type | Version Example | Changes | Backward Compatibility |
|------|----------------|---------|----------------------|
| **PATCH** | 1.0.0 → 1.0.1 | Data error fixes, typo corrections | Maintained |
| **MINOR** | 1.0.0 → 1.1.0 | Data additions, new named queries | Maintained |
| **MAJOR** | 1.0.0 → 2.0.0 | Schema changes, table deletions, manifest structure changes | Broken |

---

## Release Procedure

### Step 1: Modify Data

```bash
# Example: add new data or fix errors
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()
# ... execute SQL ...
conn.commit()
conn.close()
"
```

### Step 2: Run Tests

```bash
# Confirm all tests pass
pytest tests/ -v

# Result: 196 passed
```

### Step 3: Update Version Number

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('trilobase.db')
cursor = conn.cursor()
cursor.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")
from datetime import date
cursor.execute(\"UPDATE artifact_metadata SET value = ? WHERE key = 'created_at'\", (str(date.today()),))
conn.commit()
conn.close()
print('Version updated to 1.1.0')
"
```

### Step 4: Create .scoda Package

```bash
# Trilobase .scoda package (includes MCP tool definitions)
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json

# PaleoCore .scoda package (dependency)
python scripts/create_paleocore_scoda.py
```

### Step 5: Release Packaging

```bash
# 1. Pre-check with dry-run
python scripts/release.py --dry-run

# 2. Create the actual release
python scripts/release.py
```

**Generated files:**
```
releases/trilobase-v1.1.0/
├── trilobase.db         # Read-only copy (0444 permissions)
├── metadata.json        # Metadata + provenance + statistics
├── checksums.sha256     # SHA-256 hashes
└── README.md            # Usage instructions
```

### Step 6: Git Commit and Tagging

```bash
git add trilobase.db
git commit -m "chore: Release v1.1.0 — [summary of changes]"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main v1.1.0
```

---

## Distribution Procedure

### Step 1: PyInstaller Build

```bash
python scripts/build.py
```

**Build output:**
```
dist/
├── ScodaDesktop.exe          # GUI viewer (Windows)
├── ScodaDesktop_mcp.exe      # MCP stdio server (Claude Desktop only)
├── trilobase.scoda            # Data package
└── paleocore.scoda            # Dependency package
```

**Bundled files:**
- `scoda_engine/` (app.py, mcp_server.py, gui.py, serve.py, scoda_package.py)
- `scoda_engine/templates/`, `scoda_engine/static/`
- `spa/` (Reference Implementation SPA)
- Flask and dependencies

### Step 2: Prepare Distribution Files

```bash
# ZIP compression
cd dist
zip -r ScodaDesktop-v1.1.0-windows.zip \
  ScodaDesktop.exe ScodaDesktop_mcp.exe \
  trilobase.scoda paleocore.scoda
```

### Step 3: Create GitHub Release (Optional)

```bash
gh release create v1.1.0 \
  --title "SCODA Desktop v1.1.0" \
  --notes "Release notes here" \
  dist/ScodaDesktop-v1.1.0-windows.zip
```

---

## Overlay DB Compatibility

The Overlay DB stores user annotations and is linked to the canonical DB version.

### Compatibility Matrix

| Canonical Version Change | Overlay DB Handling | User Annotation Preservation |
|------------------------|-------------------|---------------------------|
| PATCH (1.0.0 → 1.0.1) | Version update only | Fully preserved |
| MINOR (1.0.0 → 1.1.0) | Version update only | Fully preserved |
| MAJOR (1.0.0 → 2.0.0) | Regenerate + migrate | Matched by entity_name |

### Role of entity_name

```sql
CREATE TABLE user_annotations (
    id INTEGER PRIMARY KEY,
    entity_type TEXT,        -- 'genus', 'family', etc.
    entity_id INTEGER,       -- ID in the canonical DB (may change between versions)
    entity_name TEXT,        -- 'Paradoxides', etc. (immutable, used for cross-release matching)
    annotation_type TEXT,
    content TEXT,
    created_at TEXT
);
```

- `entity_id` may differ across canonical DB versions
- `entity_name` is immutable and can be used for matching during major version upgrades

---

## Verification and Testing

### Release Integrity Verification

```bash
cd releases/trilobase-v1.1.0
sha256sum --check checksums.sha256
cat metadata.json | jq '.version, .sha256'
```

### Executable Testing

```bash
# Launch GUI
./dist/ScodaDesktop.exe

# Checklist:
# - GUI log shows "Loaded: trilobase.scoda"
# - Click "Start Server" → browser opens automatically
# - Confirm access to http://localhost:8080
# - Manifest-driven views render correctly
```

### API Testing

```bash
# Check manifest
curl http://localhost:8080/api/manifest | jq '.name'

# Execute named query
curl 'http://localhost:8080/api/queries/genera_list/execute' | jq '.row_count'

# Composite detail
curl 'http://localhost:8080/api/composite/genus_detail?id=100' | jq '.name'
```

---

## Cautions

### Immutability Principle

- **Cannot regenerate a release with the same version number**
  ```
  python scripts/release.py
  # Error: Release directory already exists
  # SCODA immutability principle: cannot overwrite an existing release.
  ```
- If a release was created by mistake: delete the directory → increment version → re-release

### Source DB Changes

- `scripts/release.py` automatically adds a `sha256` key to the source DB
- Do not forget to commit the source DB after releasing

### .scoda Package Structure

```
trilobase.scoda (ZIP)
├── manifest.json          # Package metadata
├── data.db                # Canonical SQLite DB
└── mcp_tools.json         # MCP tool definitions (optional)
```

### PyInstaller Cache

```bash
# Clear cache if build errors occur
rm -rf build/ dist/ __pycache__
python scripts/build.py
```

---

## Quick Reference

```bash
# 1. Modify data + test
pytest tests/

# 2. Update version
python3 -c "
import sqlite3; conn = sqlite3.connect('trilobase.db')
conn.execute(\"UPDATE artifact_metadata SET value = '1.1.0' WHERE key = 'version'\")
conn.commit()
"

# 3. Create .scoda package
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json

# 4. Create release
python scripts/release.py

# 5. Git commit + tag
git add trilobase.db
git commit -m "chore: Release v1.1.0"
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin main v1.1.0

# 6. Build executable
python scripts/build.py
```

---

## Related Documents

- [API_REFERENCE.md](./API_REFERENCE.md) — REST API Reference
- [MCP_GUIDE.md](./MCP_GUIDE.md) — MCP Server Usage Guide
- [HANDOFF.md](./HANDOFF.md) — Project Status and Handoff
- [SCODA_CONCEPT.md](./SCODA_CONCEPT.md) — SCODA Concept Overview

---

**Last updated:** 2026-02-14
