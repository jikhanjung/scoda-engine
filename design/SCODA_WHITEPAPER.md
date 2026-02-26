# SCODA: Self-Contained Open Data Artifact

**A Specification for Portable, Declarative Scientific Data Packages**

**Version:** 1.0 Draft
**Date:** 2026-02-14
**Reference Implementation:** SCODA Desktop + Trilobase / PaleoCore packages

---

## Abstract

SCODA (Self-Contained Open Data Artifact) is an architecture for distributing scientific data as **immutable, versioned packages**. Unlike conventional service-based data distribution (API servers, cloud databases), SCODA bundles data, schema, metadata, and UI definitions into a single self-contained file for distribution.

SCODA is composed of three core concepts:

1. **.scoda package** -- A ZIP-based distribution unit containing data and metadata
2. **SCODA Desktop** -- A generic viewer for opening and exploring .scoda packages
3. **Overlay DB** -- A layer that stores user local annotations separately on top of immutable canonical data

This document describes SCODA's design principles, package format, viewer architecture, and a validation using Trilobase (a trilobite taxonomic database) as the reference implementation.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [.scoda Package Format](#2-scoda-package-format)
3. [SCODA Metadata Layer](#3-scoda-metadata-layer)
4. [Declarative UI Manifest](#4-declarative-ui-manifest)
5. [SCODA Desktop Viewer](#5-scoda-desktop-viewer)
6. [Multi-DB Architecture](#6-multi-db-architecture)
7. [Overlay DB and Local Annotations](#7-overlay-db-and-local-annotations)
8. [MCP Server -- LLM Integration Interface](#8-mcp-server--llm-integration-interface)
9. [Build and Deployment Pipeline](#9-build-and-deployment-pipeline)
10. [Reference Implementation SPA](#10-reference-implementation-spa)
11. [Reference Implementation: Trilobase and PaleoCore](#11-reference-implementation-trilobase-and-paleocore)
12. [Appendix: File Structure and API Reference](#12-appendix-file-structure-and-api-reference)

---

## 1. Design Philosophy

### 1.1 "Not a Database, but a Knowledge Object"

Scientific data is a **publication**, not a service. Just as a paper is not modified after publication, a specific version of a dataset must also be immutable. SCODA implements this principle as a software architecture:

- **Trilobase is not a database you connect to. It is a knowledge object you open.**
- Each release is a **read-only, curated snapshot**.
- Changes to data are made only by publishing a new version.

### 1.2 Core Principles

| Principle | Description |
|-----------|-------------|
| **Immutability** | Canonical data cannot be changed after release. Modifications are made only by publishing a new version |
| **Self-Containment** | A single .scoda file contains all data, schema, metadata, and UI definitions |
| **Declarative UI** | The data itself declares how the viewer should display it (manifest) |
| **Separation of Concerns** | Canonical data (immutable) / Overlay data (user annotations) / Infrastructure data (shared) are kept separate |
| **DB is Truth, Viewer is Narration** | The DB is the single source of truth. Viewers (web, LLM) are narrators, not decision-makers |
| **Provenance Always** | Every piece of data has an explicit source. Unsupported claims are not permitted |

### 1.3 What SCODA Intentionally Does Not Do

Since SCODA is **not a service**, it intentionally excludes the following:

- Real-time collaborative editing
- Automatic merging of differing interpretations
- Using a centralized live API as the primary interface
- Implicit modification of historical data

---

## 2. .scoda Package Format

### 2.1 Physical Structure

A .scoda file is a ZIP compressed archive with only the extension changed to `.scoda`:

```
trilobase.scoda (ZIP archive)
├── manifest.json          # Package metadata
├── data.db                # SQLite database
└── assets/                # Additional resources (optional)
    └── spa/               # Reference SPA files (optional)
        ├── index.html
        ├── app.js
        └── style.css
```

### 2.2 manifest.json

The top-level metadata file containing package identity, version, dependencies, and integrity information:

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "2.1.0",
  "title": "Trilobase - A catalogue of trilobite genera",
  "description": "A catalogue of trilobite genera",
  "created_at": "2026-02-14T00:00:00+00:00",
  "license": "CC-BY-4.0",
  "authors": ["Jell, P.A.", "Adrain, J.M."],
  "data_file": "data.db",
  "record_count": 17937,
  "data_checksum_sha256": "a1b2c3d4e5f6...",
  "dependencies": [
    {
      "name": "paleocore",
      "alias": "pc",
      "version": "0.3.0",
      "file": "paleocore.scoda",
      "description": "Shared paleontological infrastructure (geography, stratigraphy)"
    }
  ],
  "has_reference_spa": true,
  "reference_spa_path": "assets/spa/"
}
```

**Key Fields:**

| Field | Description |
|-------|-------------|
| `format` / `format_version` | SCODA format identifier and version |
| `name` | Unique identifier for the package (matches the filename) |
| `version` | Semantic Versioning (MAJOR.MINOR.PATCH) |
| `data_file` | SQLite DB filename inside the ZIP |
| `record_count` | Total record count across data tables (excluding metadata tables) |
| `data_checksum_sha256` | SHA-256 checksum of data.db (for integrity verification) |
| `dependencies` | List of other .scoda packages required at runtime |
| `has_reference_spa` | Whether a Reference SPA is included |

### 2.3 Data Integrity

When opening a package, the integrity of data.db is verified using `data_checksum_sha256`:

```python
pkg = ScodaPackage("trilobase.scoda")
assert pkg.verify_checksum()  # SHA-256 verification
```

### 2.4 Package Lifecycle

```
[Source DB] → create_scoda.py → [.scoda package]
                                      ↓
                              ScodaPackage.open()
                                      ↓
                              [Extract data.db to temp dir]
                                      ↓
                              sqlite3.connect(temp/data.db)
                                      ↓
                              [ATTACH overlay + dependencies]
                                      ↓
                              [Serve via Flask/MCP]
                                      ↓
                              ScodaPackage.close()
                                      ↓
                              [Auto-cleanup temp dir]
```

- The data.db inside a .scoda file is **never accessed directly**
- It is extracted to a temporary directory and opened with SQLite; the temp dir is automatically cleaned up when the process exits
- The original .scoda file always remains immutable

---

## 3. SCODA Metadata Layer

Inside data.db, in addition to the actual data tables, there are 6 SCODA metadata tables. These tables provide package identity, provenance, schema descriptions, and UI rendering hints.

### 3.1 Table List

| Table | Role | Example Record Count |
|-------|------|---------------------|
| `artifact_metadata` | Package identity (key-value) | 7 |
| `provenance` | Data provenance and build information | 3--5 |
| `schema_descriptions` | Natural language descriptions for all tables/columns | 80--94 |
| `ui_display_intent` | Default view type hints per entity | 4--6 |
| `ui_queries` | Named SQL queries (parameterized) | 14--16 |
| `ui_manifest` | Declarative view definitions (JSON) | 1 |

### 3.2 artifact_metadata

Stores package identity as key-value pairs:

```sql
CREATE TABLE artifact_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

| key | value (example) |
|-----|-----------------|
| `artifact_id` | `trilobase` |
| `name` | `Trilobase` |
| `version` | `2.1.0` |
| `schema_version` | `1.0` |
| `created_at` | `2026-02-14` |
| `description` | `A catalogue of trilobite genera` |
| `license` | `CC-BY-4.0` |

### 3.3 provenance

Scholarly provenance and build pipeline information for the data:

```sql
CREATE TABLE provenance (
    id          INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,    -- 'reference' or 'build'
    citation    TEXT NOT NULL,
    description TEXT,
    year        INTEGER,
    url         TEXT
);
```

Example:

| id | source_type | citation | year |
|----|-------------|----------|------|
| 1 | reference | Jell, P.A. & Adrain, J.M. (2002). Available trilobite names... | 2002 |
| 2 | reference | Adrain, J.M. (2011). Class Trilobita... | 2011 |
| 3 | build | Trilobase build pipeline (2026). | 2026 |

### 3.4 schema_descriptions

Natural language descriptions for all tables and columns. Used by LLMs to understand the schema, and can also be leveraged for viewer help text:

```sql
CREATE TABLE schema_descriptions (
    table_name  TEXT NOT NULL,
    column_name TEXT,          -- NULL for table-level descriptions
    description TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);
```

### 3.5 ui_display_intent

Hints for which view type (tree, table, chart) to use for each data entity:

```sql
CREATE TABLE ui_display_intent (
    id           INTEGER PRIMARY KEY,
    entity       TEXT NOT NULL,      -- 'genera', 'countries', 'chronostratigraphy', etc.
    default_view TEXT NOT NULL,      -- 'tree', 'table', 'chart'
    description  TEXT,
    source_query TEXT,               -- References ui_queries.name
    priority     INTEGER DEFAULT 0
);
```

### 3.6 ui_queries -- Named SQL Queries

Parameterized SQL queries stored inside the DB. The viewer executes them by query name:

```sql
CREATE TABLE ui_queries (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,   -- 'taxonomy_tree', 'family_genera', 'genera_list', etc.
    description TEXT,
    sql         TEXT NOT NULL,          -- SQL to execute (parameters: :param_name)
    params_json TEXT,                   -- Default parameters (JSON)
    created_at  TEXT NOT NULL
);
```

**Core Design Intent:** SQL lives inside the DB. The viewer does not need to hardcode SQL -- it queries data using only query names and parameters. When a new data package is opened, the viewer automatically adapts based on the query list provided by that package.

```python
# Viewer code
result = execute_named_query("genera_list")
result = execute_named_query("family_genera", {"family_id": 42})
```

---

## 4. Declarative UI Manifest

### 4.1 Overview

The `ui_manifest` table declares the entire UI structure of the viewer as a single JSON document. The viewer reads this manifest and **automatically generates** tabs, tables, trees, charts, and detail modals.

```sql
CREATE TABLE ui_manifest (
    name          TEXT PRIMARY KEY,    -- 'default'
    description   TEXT,
    manifest_json TEXT NOT NULL,       -- Full UI definition (JSON)
    created_at    TEXT NOT NULL
);
```

### 4.2 Manifest Structure

```json
{
  "default_view": "taxonomy_tree",
  "views": {
    "taxonomy_tree": { ... },       // Tab view: tree
    "genera_table": { ... },        // Tab view: table
    "references_table": { ... },    // Tab view: table
    "chronostratigraphy_table": { ... },  // Tab view: chart
    "genus_detail": { ... },        // Detail view: modal
    "formation_detail": { ... },    // Detail view: modal
    ...
  }
}
```

### 4.3 View Types

| type | Description | Example |
|------|-------------|---------|
| `tree` | Hierarchical tree view (expand/collapse) | Taxonomy (Class->Order->...->Family) |
| `table` | Generic table view (sort/search) | Genera, Countries, Formations, Bibliography |
| `chart` | Specialized chart view | ICS Chronostratigraphic Chart (hierarchical color coding) |
| `detail` | Detail modal view (on row click) | Genus detail, Country detail, Formation detail |

### 4.4 Table View Definition Example

```json
{
  "type": "table",
  "title": "All Genera",
  "description": "Complete list of trilobite genera",
  "source_query": "genera_list",
  "icon": "bi-list-ul",
  "columns": [
    {"key": "name", "label": "Genus", "sortable": true, "searchable": true, "format": "italic"},
    {"key": "author", "label": "Author", "sortable": true, "searchable": true},
    {"key": "year", "label": "Year", "sortable": true},
    {"key": "family", "label": "Family", "sortable": true, "searchable": true},
    {"key": "is_valid", "label": "Valid", "sortable": true, "format": "boolean"}
  ],
  "default_sort": {"key": "name", "direction": "asc"},
  "searchable": true,
  "on_row_click": {
    "action": "open_detail",
    "detail_view": "genus_detail",
    "id_column": "id"
  }
}
```

### 4.5 Tree View Definition Example

```json
{
  "type": "tree",
  "title": "Taxonomy",
  "source_query": "taxonomy_tree",
  "icon": "bi-diagram-3",
  "tree_options": {
    "root_query": "taxonomy_tree",
    "build_from_flat": true,
    "id_field": "id",
    "parent_field": "parent_id",
    "label_field": "name",
    "item_query": "family_genera",
    "item_param": "family_id",
    "item_columns": [
      {"key": "name", "label": "Genus", "format": "italic"},
      {"key": "author", "label": "Author"},
      {"key": "year", "label": "Year"},
      {"key": "is_valid", "label": "Valid", "format": "boolean"}
    ],
    "on_node_info": {"action": "open_detail", "detail_view": "rank_detail"},
    "on_item_click": {"action": "open_detail", "detail_view": "genus_detail"},
    "item_valid_filter": {"column": "is_valid", "label": "Valid only"}
  }
}
```

### 4.6 Detail View Definition Example

```json
{
  "type": "detail",
  "title": "Genus Detail",
  "source_query": "genus_detail",
  "id_param": "id",
  "sections": [
    {
      "type": "field_grid",
      "title": "Basic Information",
      "fields": [
        {"key": "name", "label": "Name", "format": "italic"},
        {"key": "author", "label": "Author"},
        {"key": "year", "label": "Year"},
        {"key": "is_valid", "label": "Valid", "format": "boolean"},
        {"key": "type_species", "label": "Type Species", "format": "italic"},
        {"key": "temporal_code", "label": "Temporal Range", "format": "temporal_range"},
        {"key": "hierarchy", "label": "Classification", "format": "hierarchy"}
      ]
    },
    {
      "type": "linked_table",
      "title": "Formations",
      "data_key": "formations",
      "columns": [
        {"key": "name", "label": "Formation"},
        {"key": "country", "label": "Country"},
        {"key": "period", "label": "Period"}
      ],
      "on_row_click": {"action": "open_detail", "detail_view": "formation_detail"}
    },
    {"type": "annotations"}
  ]
}
```

### 4.7 Field Formats

Available field formats in the manifest:

| format | Rendering |
|--------|-----------|
| `italic` | Italic text (e.g., scientific names) |
| `boolean` | Checkmark / X mark |
| `link` | Clickable hyperlink |
| `color_chip` | Color chip (hex color) |
| `code` | Monospace code |
| `hierarchy` | Hierarchy path (Class -> Order -> ... -> Family) |
| `temporal_range` | Geological age code + ICS mapping link |
| `computed` | Runtime computed value |

### 4.8 Section Types (Detail View)

| type | Description |
|------|-------------|
| `field_grid` | Key-value field grid (2-column layout) |
| `linked_table` | Linked data table (clickable) |
| `tagged_list` | Tag-style list (regions, formations, etc.) |
| `raw_text` | Raw text (raw_entry, etc.) |
| `annotations` | User annotation section (Overlay DB) |
| `synonym_list` | Synonym list (taxonomy-specific) |
| `rank_children` | Child taxa list |
| `rank_statistics` | Child taxa statistics |
| `bibliography` | Related references |

---

## 5. SCODA Desktop Viewer

### 5.1 Components

SCODA Desktop consists of the following 4 runtime components:

```
┌─────────────────────────────────────────────────────────┐
│                    SCODA Desktop                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  GUI (tkinter)│  │ Flask Server │  │  MCP Server   │  │
│  │              │  │   (port 8080)│  │  (stdio/SSE)  │  │
│  │  • Pkg select │  │  • REST API  │  │  • 14 tools   │  │
│  │  • Start/Stop │  │  • Static    │  │  • Evidence   │  │
│  │  • Log viewer │  │    files     │  │    Pack       │  │
│  │  • SPA extract│  │  • SPA serve │  │    pattern    │  │
│  │              │  │  • CORS      │  │  • Overlay    │  │
│  │              │  │              │  │    R/W        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│         └─────────┬───────┘──────────────────┘           │
│                   ↓                                      │
│         ┌─────────────────┐                              │
│         │  scoda_package.py│  ← Central DB access module  │
│         │  PackageRegistry │                              │
│         └────────┬────────┘                              │
│                  ↓                                       │
│  ┌─────────────────────────────────────────────────┐     │
│  │          SQLite (3-DB ATTACH)                    │     │
│  │                                                  │     │
│  │  main: trilobase.db  (canonical, read-only)      │     │
│  │  overlay: trilobase_overlay.db  (user, read/write)│     │
│  │  pc: paleocore.db  (infrastructure, read-only)   │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 5.2 GUI Control Panel

A tkinter-based control panel inspired by Docker Desktop:

**Features:**
- **Package List (Listbox):** Displays discovered .scoda packages with Running/Stopped status icons
- **Server Control:** Start Server / Stop Server buttons
- **Browser Open:** Automatic / manual browser opening after server start
- **SPA Extraction:** Extract SPA from packages that include a Reference SPA
- **Real-time Logs:** Displays Flask server logs with color-coded levels (ERROR: red, WARNING: orange, INFO: blue, SUCCESS: green)
- **Dependency Display:** Shows dependencies of the running package as indented children

**Execution Modes:**

| Mode | Server Execution | Log Capture |
|------|-----------------|-------------|
| Development mode | subprocess (separate process) | stdout pipe |
| Frozen mode (PyInstaller) | threading (same process) | sys.stdout/stderr redirect |

**Package Switching Constraint:** Package switching is blocked while the server is running. The server must be stopped first before selecting a different package.

### 5.3 Flask Web Server

`app.py` (1,120 lines) provides the following:

**REST API Endpoints (22):**

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Browse** | `GET /api/tree` | Full taxonomic hierarchy tree |
| | `GET /api/family/<id>/genera` | List of genera in a family |
| | `GET /api/rank/<id>` | Taxonomic rank detail |
| | `GET /api/genus/<id>` | Genus detail (with hierarchy, synonyms, localities) |
| **Reference Data** | `GET /api/country/<id>` | Country detail + related genera |
| | `GET /api/region/<id>` | Region detail + related genera |
| | `GET /api/formation/<id>` | Formation detail + related genera |
| | `GET /api/bibliography/<id>` | Bibliography detail + related genera |
| | `GET /api/chronostrat/<id>` | ICS chronostratigraphic unit detail |
| **SCODA Meta** | `GET /api/metadata` | Package metadata + statistics |
| | `GET /api/provenance` | Data provenance |
| | `GET /api/display-intent` | View type hints |
| | `GET /api/queries` | Named query list |
| | `GET /api/queries/<name>/execute` | Execute named query |
| | `GET /api/manifest` | UI manifest |
| **Generic** | `GET /api/detail/<query_name>` | Generic detail based on named query |
| **PaleoCore** | `GET /api/paleocore/status` | PaleoCore DB status + cross-DB validation |
| **Overlay** | `GET /api/annotations/<type>/<id>` | Retrieve user annotations |
| | `POST /api/annotations` | Add user annotation |
| | `DELETE /api/annotations/<id>` | Delete user annotation |
| **Static** | `GET /` | Main page (SPA or generic viewer) |
| | `GET /<path>` | SPA static file serving |

**CORS Support:** All responses include `Access-Control-Allow-Origin` headers to allow access from external SPAs.

**Package Selection:** The active package is specified via the `--package` CLI argument or `set_active_package()` call. Flask always serves **only one package** at a time.

### 5.4 Generic Frontend

`static/js/app.js` (1,399 lines) is a manifest-driven, generic SCODA viewer:

**Rendering Pipeline:**

```
1. loadManifest()           ← Calls /api/manifest
2. buildViewTabs()          ← Generates tabs from manifest.views
3. switchToView(viewKey)    ← On tab click
4. Branch by view.type:
   ├── "tree"  → loadTree() → buildTreeFromFlat()
   ├── "table" → loadTableView() → renderTableView()
   └── "chart" → loadChartView() → renderChartView()
5. On row click:
   on_row_click.action === "open_detail"
   → openDetail(detail_view, id)
   → renderDetailFromManifest(data, viewDef)
```

**Characteristics:**
- **Package-agnostic:** Automatically generates tabs/tables/detail modals for any .scoda package with a manifest, not just Trilobase
- **Graceful degradation:** Falls back to legacy UI if no manifest is present
- **Package name display:** Shows the active package name and version in the navbar

---

## 6. Multi-DB Architecture

### 6.1 SQLite ATTACH Pattern

SCODA leverages SQLite's `ATTACH DATABASE` feature to query data from multiple packages within a single connection:

```sql
-- Main connection
conn = sqlite3.connect('trilobase.db')

-- Overlay DB connection (user annotations)
ATTACH DATABASE 'trilobase_overlay.db' AS overlay

-- PaleoCore DB connection (shared infrastructure data)
ATTACH DATABASE 'paleocore.db' AS pc
```

This enables cross-DB JOINs:

```sql
-- JOIN Trilobase genus_locations with PaleoCore countries
SELECT g.name, c.name AS country
FROM genus_locations gl
JOIN taxonomic_ranks g ON gl.genus_id = g.id
JOIN pc.countries c ON gl.country_id = c.id
WHERE c.name = 'China';
```

### 6.2 PackageRegistry

The `PackageRegistry` class in `scoda_package.py` centrally manages package discovery and DB connections:

```python
registry = PackageRegistry()
registry.scan("/path/to/packages/")  # Discover *.scoda files

# Package list
for pkg in registry.list_packages():
    print(f"{pkg['name']} v{pkg['version']} ({pkg['record_count']} records)")

# DB connection (auto-ATTACH dependencies)
conn = registry.get_db("trilobase")
# → main: trilobase data.db
# → overlay: trilobase_overlay.db
# → pc: paleocore data.db (dependency)
```

**Discovery Priority:**
1. Discover `*.scoda` files -> Extract data.db from ZIP
2. If no .scoda files found, use `*.db` files directly (fallback)

**Dependency Resolution:**
Reads the `dependencies` array from manifest.json and finds the corresponding .scoda packages in the same directory, attaching them with their `alias`.

### 6.3 3-DB Role Separation

| DB | Alias | Access | Role |
|----|-------|--------|------|
| trilobase.db | (main) | Read-only | Taxonomic data (genus, synonym, bibliography) |
| trilobase_overlay.db | overlay | Read/Write | User annotations |
| paleocore.db | pc | Read-only | Shared infrastructure (country, formation, ICS chronostratigraphy) |

### 6.4 Logical Foreign Key

Cross-package references are managed via **logical foreign keys** rather than SQLite FOREIGN KEY constraints:

| Source (Trilobase) | Target (PaleoCore) | Reference Meaning |
|---|---|---|
| `genus_locations.country_id` | `pc.countries.id` | Genus occurrence country |
| `genus_locations.region_id` | `pc.geographic_regions.id` | Genus occurrence region |
| `genus_formations.formation_id` | `pc.formations.id` | Genus occurrence formation |
| `taxonomic_ranks.temporal_code` | `pc.temporal_ranges.code` | Genus geological age |

---

## 7. Overlay DB and Local Annotations

### 7.1 Design Principles

One of SCODA's core principles is the **immutability of canonical data**. However, scientists want to leave notes on data, record alternative interpretations, and add external literature links. The Overlay DB satisfies both requirements simultaneously:

- Canonical data is never modified
- User local annotations are stored in a separate file
- Annotations are displayed alongside canonical data but are visually distinguished

### 7.2 Overlay DB Schema

```sql
-- Version tracking
CREATE TABLE overlay_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- key: 'canonical_version', 'created_at'

-- User annotations
CREATE TABLE user_annotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL,      -- 'genus', 'family', 'order', ...
    entity_id       INTEGER NOT NULL,   -- ID in the canonical DB
    entity_name     TEXT,               -- Name (for cross-release matching)
    annotation_type TEXT NOT NULL,      -- 'note', 'correction', 'alternative', 'link'
    content         TEXT NOT NULL,
    author          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7.3 Role of entity_name

`entity_id` may change between canonical DB versions. In contrast, `entity_name` (e.g., "Paradoxides") is stable. During a major version upgrade, annotations can be mapped to new IDs using entity_name.

### 7.4 Annotation Types

| type | Purpose | Example |
|------|---------|---------|
| `note` | General memo | "See Smith (2020) regarding this genus" |
| `correction` | Data error report | "Author name is incorrect, should be ZHANG, 1981" |
| `alternative` | Alternative taxonomic interpretation | "Adrain (2011) reassigned this genus to Aulacopleuridae" |
| `link` | External link | "https://paleobiodb.org/classic/displayReference?id=12345" |

### 7.5 Version Compatibility

| Canonical Version Change | Overlay Handling | Annotation Preservation |
|--------------------------|-----------------|------------------------|
| PATCH (1.0.0 -> 1.0.1) | Version update only | Fully preserved |
| MINOR (1.0.0 -> 1.1.0) | Version update only | Fully preserved |
| MAJOR (1.0.0 -> 2.0.0) | Regeneration + migration | Matched via entity_name |

---

## 8. MCP Server -- LLM Integration Interface

### 8.1 Overview

The MCP (Model Context Protocol) server is an interface that enables LLMs (Large Language Models) to query data in SCODA packages using natural language.

**Core Principle: DB is truth, MCP is access, LLM is narration**

- The LLM does not judge or define the data
- The LLM only narrates the evidence provided by the DB
- Every response includes provenance

### 8.2 14 MCP Tools

| Category | Tool | Description |
|----------|------|-------------|
| **Taxonomy** | `get_taxonomy_tree` | Full taxonomic hierarchy tree |
| | `get_rank_detail` | Taxonomic rank detail |
| | `get_family_genera` | List of genera in a family |
| **Search** | `search_genera` | Genus name pattern search |
| | `get_genera_by_country` | Query genera by country |
| | `get_genera_by_formation` | Query genera by formation |
| **Meta** | `get_metadata` | Package metadata + statistics |
| | `get_provenance` | Data provenance |
| | `list_available_queries` | Named query list |
| **Query** | `execute_named_query` | Execute named query |
| **Annotations** | `get_annotations` | Retrieve user annotations |
| | `add_annotation` | Add annotation (Overlay DB) |
| | `delete_annotation` | Delete annotation |
| **Detail** | `get_genus_detail` | Genus Evidence Pack |

### 8.3 Evidence Pack Pattern

`get_genus_detail` returns not a simple record but an **Evidence Pack**. This is a structured response that enables the LLM to produce evidence-based narration:

```json
{
  "genus": {
    "id": 42,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": true,
    "family": "Paradoxididae",
    "type_species": "Entomostracites paradoxissimus",
    "raw_entry": "PARADOXIDES BRONGNIART, 1822 ..."
  },
  "synonyms": [...],
  "formations": [...],
  "localities": [...],
  "references": [...],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "2.1.0",
    "extraction_date": "2026-02-04"
  }
}
```

### 8.4 Execution Modes

| Mode | Protocol | Use Case |
|------|----------|----------|
| **stdio** | stdin/stdout | Direct execution from Claude Desktop |
| **SSE** | HTTP (Starlette + uvicorn) | Execution from GUI on port 8081 |

**stdio Mode Usage (Claude Desktop Configuration):**

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "ScodaDesktop_mcp.exe"
    }
  }
}
```

---

## 9. Build and Deployment Pipeline

### 9.1 Deployment Artifacts

```
dist/
├── ScodaDesktop.exe        # GUI viewer (Windows, console=False)
├── ScodaDesktop_mcp.exe    # MCP stdio server (Windows, console=True)
├── trilobase.scoda         # Trilobase data package
└── paleocore.scoda         # PaleoCore infrastructure package
```

**User Deployment:** Place the above 4 files in the same directory and run `ScodaDesktop.exe`. No separate installation required.

### 9.2 Build Process

```
python scripts/build.py
    │
    ├── 1. Build EXE with PyInstaller
    │   ├── ScodaDesktop.exe  ← scripts/gui.py entry point
    │   │   Bundles: app.py, scoda_package.py, templates/, static/, spa/
    │   └── ScodaDesktop_mcp.exe ← mcp_server.py entry point
    │       Bundles: scoda_package.py
    │
    ├── 2. Create trilobase.scoda
    │   trilobase.db → ZIP(manifest.json + data.db + assets/spa/*)
    │
    └── 3. Create paleocore.scoda
        paleocore.db → ZIP(manifest.json + data.db)
```

**Key Design Decision:** The DB is not bundled inside the EXE. Data is separated externally as .scoda packages, and the EXE discovers .scoda files in the same directory at runtime.

### 9.3 Release Process

```
1. Data modifications + testing (pytest, 230 tests)
2. Update artifact_metadata version
3. Run scripts/release.py → Package into releases/ directory
4. Git commit + tag (v2.1.0)
5. Run scripts/build.py → Generate dist/
6. GitHub Release or direct distribution
```

**Immutability Guarantee:** A release cannot be regenerated with the same version number. `release.py` raises an error if the directory already exists.

### 9.4 Semantic Versioning

| Type | Version Example | Change Description |
|------|----------------|-------------------|
| PATCH | 1.0.0 -> 1.0.1 | Data error fixes, typos |
| MINOR | 1.0.0 -> 1.1.0 | Data additions, new tables |
| MAJOR | 1.0.0 -> 2.0.0 | Schema changes, table removals |

---

## 10. Reference Implementation SPA

### 10.1 Generic Viewer vs. Reference SPA

SCODA Desktop distinguishes between two types of frontends:

| | Generic Viewer | Reference SPA |
|---|---|---|
| Location | `static/js/app.js` (embedded in EXE) | `spa/` (inside package at `assets/spa/`) |
| Target | All .scoda packages | Specific package only |
| Dependencies | Jinja2 templates | Independent (pure HTML/JS/CSS) |
| Custom Logic | None (depends only on manifest) | Includes package domain-specific functions |
| API Access | `/api/...` (same-origin) | `API_BASE + '/api/...'` (configurable) |

### 10.2 Automatic SPA Switching

1. User clicks "Extract Reference SPA" in the GUI
2. Extracts `assets/spa/*` files from the .scoda package to a `<name>_spa/` directory
3. When Flask detects `<name>_spa/index.html`, it automatically switches to SPA serving
4. If no SPA exists, falls back to generic viewer (templates/index.html)

### 10.3 Reference SPA Structure

```
spa/
├── index.html    # Standalone HTML without Jinja2
├── app.js        # Uses API_BASE prefix, includes domain-specific functions
└── style.css     # Domain-specific styles such as rank colors
```

**API_BASE Pattern:**

```javascript
// spa/app.js
if (typeof API_BASE === 'undefined') var API_BASE = '';

// In all fetch calls:
const response = await fetch(API_BASE + '/api/manifest');
```

This allows hosting the SPA on a different server while pointing the API to SCODA Desktop.

---

## 11. Reference Implementation: Trilobase and PaleoCore

### 11.1 Trilobase Package

A genus-level taxonomic database for trilobites. Extracted and curated from the Jell & Adrain (2002) PDF.

**Data Scale:**

| Item | Count |
|------|-------|
| Taxonomic ranks (Class to Genus) | 5,340 |
| Valid genera | 4,260 (83.3%) |
| Invalid genera (synonyms, etc.) | 855 (16.7%) |
| Synonym relationships | 1,055 |
| Genus-Formation relationships | 4,853 |
| Genus-Country relationships | 4,841 |
| References | 2,130 |

**Taxonomic Hierarchy:**

```
Trilobita (Class, 1)
├── Agnostida (Order, one of 12)
│   ├── Agnostina (Suborder)
│   │   ├── Agnostoidea (Superfamily)
│   │   │   ├── Agnostidae (Family)
│   │   │   │   ├── Agnostus (Genus, valid)
│   │   │   │   ├── Acadagnostus (Genus, valid)
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

### 11.2 PaleoCore Package

Infrastructure reference data commonly needed by paleontological databases. Separated from Trilobase into an independent package.

**Data Scale:**

| Table | Records | Source |
|-------|---------|--------|
| countries | 142 | Jell & Adrain (2002) |
| geographic_regions | 562 | 60 countries + 502 regions |
| cow_states | 244 | Correlates of War v2024 |
| country_cow_mapping | 142 | Manual mapping |
| formations | 2,004 | Jell & Adrain (2002) |
| temporal_ranges | 28 | Geological age codes |
| ics_chronostrat | 178 | ICS GTS 2020 (SKOS/RDF) |
| temporal_ics_mapping | 40 | Manual mapping |
| **Total** | **3,340** | |

**PaleoCore is a root package with no dependencies.** While Trilobase depends on PaleoCore, PaleoCore can be used independently. In the future, other paleontological databases (e.g., brachiopods, cephalopods) can share the same PaleoCore.

### 11.3 Inter-Package Relationships

```
                            ┌───────────────────┐
                            │    PaleoCore       │
                            │   (paleocore.scoda)│
                            │                    │
                            │  countries (142)   │
                            │  formations (2,004)│
                            │  ics_chronostrat   │
                            │  temporal_ranges   │
                            │  ...               │
                            └────────▲───────────┘
                                     │
                              ATTACH AS pc
                                     │
┌────────────────────────────────────┤
│                                    │
│    Trilobase (trilobase.scoda)     │
│                                    │
│    taxonomic_ranks (5,340) ────────┤ temporal_code → pc.temporal_ranges
│    synonyms (1,055)                │
│    bibliography (2,130)            │
│    genus_locations (4,841) ────────┤ country_id → pc.countries
│    genus_formations (4,853) ───────┤ formation_id → pc.formations
│                                    │
└────────────────────────────────────┘
```

---

## 12. Appendix: File Structure and API Reference

### 12.1 Project File Structure

```
trilobase/
├── scoda_package.py          # .scoda package + PackageRegistry + central DB access
├── app.py                    # Flask web server (22 endpoints, 1,120 lines)
├── mcp_server.py             # MCP server (14 tools, stdio/SSE, 764 lines)
├── scripts/
│   ├── gui.py                # GUI control panel (tkinter, 859 lines)
│   ├── serve.py              # CLI server launcher
│   ├── build.py              # PyInstaller build automation
│   ├── create_scoda.py       # trilobase.db → trilobase.scoda
│   ├── create_paleocore.py   # trilobase.db → paleocore.db
│   └── create_paleocore_scoda.py  # paleocore.db → paleocore.scoda
├── templates/
│   └── index.html            # Generic viewer HTML (Jinja2)
├── static/
│   ├── css/style.css         # Generic viewer CSS (621 lines)
│   └── js/app.js             # Generic viewer JS (1,399 lines)
├── spa/                      # Reference Implementation SPA
│   ├── index.html
│   ├── app.js                # Full-featured JS (1,569 lines)
│   └── style.css             # Domain-specific CSS (626 lines)
├── examples/
│   └── genus-explorer/index.html  # Custom SPA example
├── ScodaDesktop.spec         # PyInstaller build configuration
├── trilobase.db              # Canonical SQLite DB (5.4 MB)
├── paleocore.db              # PaleoCore SQLite DB (332 KB)
├── test_app.py               # Flask tests (213 tests)
├── test_mcp_basic.py         # MCP basic test (1 test)
├── test_mcp.py               # MCP comprehensive tests (16 tests)
└── docs/
    ├── HANDOFF.md            # Project status
    ├── RELEASE_GUIDE.md       # Release guide
    ├── SCODA_CONCEPT.md       # SCODA concept document
    └── paleocore_schema.md    # PaleoCore schema reference
```

### 12.2 Technology Stack

| Component | Technology |
|-----------|-----------|
| Database | SQLite 3 (ATTACH, Cross-DB JOIN) |
| Web Server | Flask (WSGI) + CORS |
| MCP Server | mcp SDK + Starlette + uvicorn (ASGI) |
| GUI | tkinter (Python standard library) |
| Frontend | Vanilla JavaScript + Bootstrap 5 |
| Packaging | PyInstaller (onefile, Windows/Linux) |
| Testing | pytest + pytest-asyncio (230 tests) |
| Package Format | ZIP (extension .scoda) |

### 12.3 Test Status

| File | Test Count | Scope |
|------|-----------|-------|
| `test_app.py` | 213 | Flask API, CORS, manifest, detail, SPA serving |
| `test_mcp_basic.py` | 1 | MCP server initialization |
| `test_mcp.py` | 16 | MCP 14 tools + Evidence Pack |
| **Total** | **230** | |

---

**End of document.**
