# SCODA Engine

Runtime engine for **SCODA** (Self-Contained Data Artifacts) — a format for packaging structured data with metadata, queries, and UI manifests into self-describing `.scoda` ZIP archives.

SCODA Engine provides a generic viewer, API server, and MCP server that can open any `.scoda` package — no domain-specific code required.

## What is SCODA?

A `.scoda` package bundles:
- **SQLite database** with structured data
- **UI manifest** defining views (tables, trees, charts, detail modals, timelines)
- **Named queries** for reusable SQL
- **Entity schemas** for CRUD editing
- **Provenance** and schema documentation
- Optional **MCP tools** for LLM integration

## Features

- **Multi-package serving**: serve multiple `.scoda` packages simultaneously with landing page
- **Manifest-driven UI**: views, detail modals, and actions defined in DB — zero frontend code needed
- **Tree visualization**: radial, rectangular, side-by-side comparison, diff view (D3-based)
- **Timeline sub-view**: animated playback across time axes with morph transitions and video export
- **Bar chart sub-view**: stacked bar chart with rank-based grouping
- **CRUD framework**: manifest-driven entity editing with FK autocomplete, constraints, and hooks
- **3-DB architecture**: canonical (read-only) + overlay (user edits) + dependency (ATTACH)
- **Mobile responsive**: hamburger menu, slide-out tree drawer, adaptive controls
- **MCP server**: 7 built-in tools + dynamic tools from `.scoda` packages (stdio + SSE)
- **Hub integration**: static registry for package discovery, download, and auto-update
- **Docker deployment**: production-ready with gunicorn
- **Offline support**: all vendor JS/CSS bundled (D3, Bootstrap, icons)

## Installation

```bash
pip install -e ./core          # Core library (pure stdlib, no dependencies)
pip install -e ".[dev]"        # Desktop/server + dev tools
```

## Usage

### Web Viewer

```bash
# Serve a .scoda package
scoda-serve --scoda-path mydata.scoda

# Serve all .scoda files in a directory
scoda-serve --scoda-path /path/to/packages/

# Admin mode (CRUD editing)
scoda-serve --db-path mydata.db --mode admin

# Or via python module
python -m scoda_engine.serve --scoda-path mydata.scoda
```

Opens a web viewer at `http://localhost:8080`. With multiple packages, a landing page is shown; with a single package, redirects directly to the viewer.

### Production Deployment

```bash
# gunicorn (requires [web] extra)
pip install -e ".[web]"
scoda-web --scoda-path /path/to/packages/

# Docker
cd deploy
docker compose up
```

### MCP Server (for LLM integration)

```bash
# stdio mode (for Claude Desktop)
scoda-mcp --package mydata.scoda

# SSE mode (integrated with web server)
scoda-serve --scoda-path mydata.scoda
# MCP available at http://localhost:8080/mcp/sse
```

### GUI Control Panel

```bash
python launcher_gui.py
# Or with a specific package
python launcher_gui.py --scoda-path mydata.scoda
```

Tkinter-based control panel with package management, Hub sync, server start/stop, and log viewer.

### PyInstaller Build

```bash
python scripts/build.py
```

Produces `ScodaDesktop.exe` (GUI) and `ScodaMCP.exe` (MCP stdio).

## Testing

```bash
pytest tests/   # 303 tests
```

## Project Structure

```
scoda-engine/
├── core/                       # scoda-engine-core (PyPI, pure stdlib, zero deps)
│   └── scoda_engine_core/
│       ├── scoda_package.py    # .scoda ZIP, DB access, PackageRegistry
│       ├── hub_client.py       # Hub: fetch index, compare, download
│       └── validate_manifest.py # Manifest validator/linter
├── scoda_engine/               # Desktop/server package
│   ├── app.py                  # FastAPI server (multi-package APIRouter + CRUD)
│   ├── entity_schema.py        # FieldDef/EntitySchema parser + validation
│   ├── crud_engine.py          # Generic CRUD engine (FK, constraints, hooks)
│   ├── mcp_server.py           # MCP server (stdio + SSE)
│   ├── gui.py                  # Tkinter GUI control panel
│   ├── serve.py                # uvicorn launcher
│   ├── serve_web.py            # Production launcher (gunicorn/Docker)
│   ├── templates/              # index.html (viewer) + landing.html (multi-package)
│   └── static/                 # CSS, JS (app.js, tree_chart.js), vendor libs
├── deploy/                     # Docker deployment (Dockerfile, docker-compose.yml)
├── scripts/                    # Build, release, validation, version bump tools
└── tests/                      # Runtime, MCP, Hub client, CRUD tests
```

## License

MIT
