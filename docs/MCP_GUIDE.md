# SCODA Desktop MCP Server Guide

**Model Context Protocol (MCP) Server Usage Guide**

**Version:** 2.0.0

---

## Table of Contents

- [Overview](#overview)
- [Installation and Setup](#installation-and-setup)
- [MCP Tool Structure](#mcp-tool-structure)
- [Builtin Tools (7)](#builtin-tools-7)
- [Dynamic Tools](#dynamic-tools)
- [Usage Examples](#usage-examples)
- [SCODA Principles](#scoda-principles)
- [Troubleshooting](#troubleshooting)

---

## Overview

The SCODA Desktop MCP server enables LLMs to query data from `.scoda` packages through the **Model Context Protocol**.

### Key Features

- **7 Builtin Tools**: Available across all `.scoda` packages (metadata, provenance, queries, annotations)
- **Dynamic Tools**: Dynamically loaded from `mcp_tools.json` within `.scoda` packages for domain-specific tools
- **Domain-Agnostic**: No domain-specific logic in runtime code
- **SCODA Principles**: DB is truth, MCP is access, LLM is narration

### Architecture

```
┌─────────────────┐
│   Claude/LLM    │ (natural language queries)
└────────┬────────┘
         │ JSON-RPC (stdio)
         ▼
┌───────────────────────────────────┐
│  ScodaDesktop_mcp.exe             │
│  - 7 builtin tools (always)      │
│  - N dynamic tools (per package) │
│  - SQL validation layer          │
└────────┬──────────────────────────┘
         │ Direct DB access
         ▼
┌───────────────────────────────────┐
│  .scoda Package                   │
│  ├── data.db (Canonical, R/O)    │
│  ├── manifest.json               │
│  └── mcp_tools.json (optional)   │
│                                   │
│  Overlay DB (R/W, annotations)   │
└───────────────────────────────────┘
```

### Two Executables

| File | Purpose | How to Run |
|------|---------|------------|
| `ScodaDesktop.exe` | GUI viewer (Flask web server + browser) | Double-click or CLI |
| `ScodaDesktop_mcp.exe` | MCP stdio server (for Claude Desktop) | Auto-spawned by Claude Desktop |

---

## Installation and Setup

### Installing Dependencies

**Basic (stdio mode):**
```bash
pip install mcp>=1.0.0
```

**Additional for SSE mode:**
```bash
pip install mcp>=1.0.0 starlette uvicorn
```

### Claude Desktop Configuration

#### Method 1: Using ScodaDesktop_mcp.exe (Recommended)

**File:** `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "scoda-desktop": {
      "command": "C:\\path\\to\\ScodaDesktop_mcp.exe"
    }
  }
}
```

#### Method 2: Using Python Source (For Developers)

**macOS/Linux:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scoda-desktop": {
      "command": "python3",
      "args": ["-m", "scoda_engine.mcp_server"],
      "cwd": "/absolute/path/to/trilobase"
    }
  }
}
```

**Restart Claude Desktop after updating the configuration.**

### Running the MCP Server Manually

```bash
# stdio mode (default)
python -m scoda_engine.mcp_server

# SSE mode
python -m scoda_engine.mcp_server --mode sse --port 8081

# Health check
curl http://localhost:8081/health
```

---

## MCP Tool Structure

The tools in the SCODA Desktop MCP server are divided into two layers:

| Layer | Tool Count | Source | Description |
|-------|-----------|--------|-------------|
| **Builtin** | 7 (fixed) | Runtime code | Common to all `.scoda` packages |
| **Dynamic** | Per package | `mcp_tools.json` | Domain-specific tools |

**When `list_tools` is called**: The 7 builtin tools and N dynamic tools are combined and returned together.

---

## Builtin Tools (7)

General-purpose tools that are always available across all `.scoda` packages.

### 1. `get_metadata`

Retrieves SCODA artifact metadata.

**Parameters:** None

**Response:**
```json
{
  "artifact_id": "trilobase",
  "name": "Trilobase",
  "version": "1.0.0",
  "description": "A taxonomic database of trilobite genera",
  "license": "CC-BY-4.0",
  "created_at": "2026-02-04"
}
```

---

### 2. `get_provenance`

Retrieves data provenance information.

**Parameters:** None

**Response:**
```json
[
  {
    "id": 1,
    "source_type": "primary",
    "citation": "Jell, P.A. & Adrain, J.M. 2002",
    "description": "Available Generic Names for Trilobites",
    "year": 2002,
    "url": null
  }
]
```

---

### 3. `list_available_queries`

Retrieves the list of available Named Queries.

**Parameters:** None

**Response:**
```json
[
  {
    "id": 1,
    "name": "taxonomy_tree",
    "description": "Get full taxonomy tree from Class to Family",
    "params_json": "{}",
    "created_at": "2026-02-05 10:00:00"
  }
]
```

---

### 4. `execute_named_query`

Executes a predefined Named Query.

**Parameters:**
- `query_name` (string, required): Query name
- `params` (object, optional): Query parameters (default: {})

**Response:**
```json
{
  "query": "taxonomy_tree",
  "columns": ["id", "name", "rank"],
  "row_count": 225,
  "rows": [...]
}
```

---

### 5. `get_annotations`

Retrieves user annotations for a specific entity.

**Parameters:**
- `entity_type` (string, required): `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `entity_id` (integer, required): Entity ID

**Response:**
```json
[
  {
    "id": 1,
    "entity_type": "genus",
    "entity_id": 100,
    "entity_name": "Paradoxides",
    "annotation_type": "note",
    "content": "Check formation data for accuracy",
    "author": "researcher_1",
    "created_at": "2026-02-09 10:00:00"
  }
]
```

---

### 6. `add_annotation`

Adds a new annotation (writes to Overlay DB).

**Parameters:**
- `entity_type` (string, required): Entity type
- `entity_id` (integer, required): Entity ID
- `entity_name` (string, required): Entity name (used for matching across releases)
- `annotation_type` (string, required): `note`, `correction`, `alternative`, `link`
- `content` (string, required): Annotation content
- `author` (string, optional): Author

**Response:** The created annotation object

---

### 7. `delete_annotation`

Deletes an annotation.

**Parameters:**
- `annotation_id` (integer, required): Annotation ID

**Response:**
```json
{
  "message": "Annotation with ID 1 deleted."
}
```

---

## Dynamic Tools

### Overview

If a `.scoda` package contains an `mcp_tools.json` file, the tools defined within it are automatically registered with the MCP server. This allows **domain-specific MCP tools to be provided through the package alone, without modifying runtime code**.

### mcp_tools.json Structure

```json
{
  "version": "1.0",
  "tools": [
    {
      "name": "search_genera",
      "description": "Search genera by name pattern",
      "input_schema": {
        "type": "object",
        "properties": {
          "name_pattern": {"type": "string", "description": "SQL LIKE pattern"},
          "limit": {"type": "integer", "description": "Max results", "default": 50}
        },
        "required": ["name_pattern"]
      },
      "query_type": "single",
      "sql": "SELECT id, name, author, year FROM taxonomic_ranks WHERE rank='Genus' AND name LIKE :name_pattern LIMIT :limit",
      "default_params": {"limit": 50}
    }
  ]
}
```

### Three Query Types

| query_type | Description | Required Fields |
|-----------|-------------|-----------------|
| `single` | Executes SQL directly | `sql` |
| `named_query` | Executes a named query from the `ui_queries` table | `named_query`, `param_mapping` |
| `composite` | Executes a composite query from a manifest detail view | `view_name`, `param_mapping` |

#### single Example

```json
{
  "name": "search_genera",
  "query_type": "single",
  "sql": "SELECT id, name, author FROM taxonomic_ranks WHERE name LIKE :name_pattern LIMIT :limit",
  "default_params": {"limit": 50}
}
```

#### named_query Example

```json
{
  "name": "get_genera_by_country",
  "query_type": "named_query",
  "named_query": "genera_by_country",
  "param_mapping": {"country": "country", "limit": "limit"},
  "default_params": {"limit": 50}
}
```

#### composite Example

```json
{
  "name": "get_genus_detail",
  "query_type": "composite",
  "view_name": "genus_detail",
  "param_mapping": {"genus_id": "id"}
}
```

### SQL Security

`single` queries from dynamic tools are validated by `_validate_sql()`:
- Only `SELECT` and `WITH` statements are allowed
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, etc. are rejected
- Parameters use `:param` binding to prevent SQL injection

### Trilobase mcp_tools.json Example

The Trilobase package provides 7 domain-specific tools via `mcp_tools.json`:

| Tool | query_type | Description |
|------|-----------|-------------|
| `get_taxonomy_tree` | single | Taxonomic hierarchy tree |
| `search_genera` | single | Search by name pattern |
| `get_genus_detail` | composite | Genus detail (composite) |
| `get_rank_detail` | composite | Rank detail (composite) |
| `get_family_genera` | named_query | List of genera in a family |
| `get_genera_by_country` | named_query | Genera by country |
| `get_genera_by_formation` | named_query | Genera by formation |

---

## Usage Examples

### Natural Language Queries in Claude Desktop

Once the MCP server is connected, you can query using natural language in Claude Desktop.

#### 1. Metadata Lookup

**Question:** "Tell me about this database"

**Claude's behavior:**
1. Calls the `get_metadata` tool
2. Analyzes and summarizes the package information

---

#### 2. Using Named Queries

**Question:** "Show me the list of available queries"

**Claude's behavior:**
1. Calls the `list_available_queries` tool
2. Organizes the query list

**Follow-up question:** "Run the taxonomy_tree query"

**Claude's behavior:**
1. Executes the query using the `execute_named_query` tool
2. Summarizes the results

---

#### 3. Using Dynamic Tools (Trilobase Package)

**Question:** "Tell me about Paradoxides in detail"

**Claude's behavior:**
1. Searches using the `search_genera` (dynamic) tool
2. Retrieves composite detail using the `get_genus_detail` (dynamic) tool
3. Narrates with source citations

---

#### 4. Annotation Workflow

```
1. "Show me the formation information for Agnostus"
   -> execute_named_query or dynamic tool

2. "Add a correction annotation to Agnostus: 'Formation name needs verification'"
   -> add_annotation

3. "Show me my annotations for Agnostus"
   -> get_annotations

4. "Delete annotation #5"
   -> delete_annotation
```

---

## SCODA Principles

### Core Principles

#### 1. DB is truth
- The database is the single source of truth
- The LLM uses only data from the DB

#### 2. MCP is access
- MCP is merely a means of access
- It does not modify data (except annotations)

#### 3. LLM is narration
- The LLM only performs evidence-based narration
- It does not make judgments or definitions
- It always cites sources

### Correct Usage Patterns

**Citing sources:**
> According to Jell & Adrain (2002), Paradoxides...

**Stating uncertainty:**
> The database lists this as Middle Cambrian, though the exact age is not specified.

**Data-based narration:**
> Based on the formation data, this genus has been found in Czech Republic and Morocco.

### Non-Goals (What the LLM Should Not Do)

- Taxonomic judgments or definitions (information not in the DB)
- Autonomous decision-making or planning
- Writing to the database (except annotations)

---

## Troubleshooting

### Issue 1: MCP Server Does Not Connect

**Symptom:** Tools are not visible in Claude Desktop

**Checklist:**
1. Configuration file path: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
2. Use absolute paths (relative paths are not supported)
3. Verify that `.scoda` or `.db` files are in the same directory as the executable
4. Restart Claude Desktop

---

### Issue 2: "Database not found" Error

**Cause:** The MCP server cannot find the data file

**Solution:**
1. Verify that the `.scoda` package or `.db` file is in the working directory
2. When using Python source, check the `cwd` setting

---

### Issue 3: Dynamic Tools Not Loading

**Cause:** The `.scoda` package does not contain `mcp_tools.json`

**Check:**
```bash
# Inspect the contents of the .scoda file
python -c "
import zipfile
with zipfile.ZipFile('trilobase.scoda') as z:
    print(z.namelist())
"
# mcp_tools.json should be in the list
```

**Solution:**
```bash
# Rebuild .scoda with mcp_tools.json included
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json
```

---

### Issue 4: Overlay DB Write Error

**Symptom:** "read-only database" error when adding annotations

**Solution:**
1. Check overlay DB file permissions: `chmod 644 trilobase_overlay.db`
2. Restart the server if the overlay DB was not auto-created

---

### Issue 5: SQL Validation Error

**Symptom:** "SQL validation failed" error when executing a dynamic tool

**Cause:** The SQL in `mcp_tools.json` contains statements other than SELECT/WITH

**Solution:** Edit the SQL in `mcp_tools.json` to use read-only queries only

---

## References

### Official Documentation

- **MCP Protocol**: https://modelcontextprotocol.io/
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop Setup**: https://modelcontextprotocol.io/clients/claude-desktop

### SCODA Desktop Documentation

- [API Reference](API_REFERENCE.md) — REST API Reference
- [SCODA Concept](SCODA_CONCEPT.md) — SCODA Concept Overview
- [Handoff](HANDOFF.md) — Project Status

---

## Version History

- **v2.0.0** (2026-02-14): Domain-agnostic MCP Server (Phase 46)
  - Removed 7 legacy domain functions
  - Two-layer structure: 7 builtin + N dynamic tools
  - Dynamic tools: Auto-loaded from `mcp_tools.json` within `.scoda` packages
  - Three query_type options: `single`, `named_query`, `composite`
  - SQL validation layer (only SELECT/WITH allowed)
  - Server name: `"scoda-desktop"`

- **v1.3.0** (2026-02-10): EXE Separation
  - `ScodaDesktop.exe` (GUI) + `ScodaDesktop_mcp.exe` (MCP stdio)
  - Simplified Claude Desktop configuration

- **v1.1.0** (2026-02-10): SSE Mode Added
  - SSE transport mode support + Health check endpoint

- **v1.0.0** (2026-02-09): Initial release
  - 14 hardcoded tools (legacy)
  - Evidence Pack pattern
  - stdio mode

---

**Last Updated:** 2026-02-14
