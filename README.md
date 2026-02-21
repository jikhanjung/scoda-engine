# SCODA Engine

Runtime engine for **SCODA** (Self-Contained Data Artifacts) — a format for packaging structured data with metadata, queries, and UI manifests into self-describing `.scoda` ZIP archives.

## What is SCODA?

A `.scoda` package bundles:
- **SQLite database** with structured data
- **Manifest** defining views (tables, trees, charts, detail modals)
- **Named queries** for reusable SQL
- **Provenance** and schema documentation
- Optional **MCP tools** for LLM integration

SCODA Engine provides a generic viewer and API server that can open any `.scoda` package.

## Installation

```bash
pip install -e ./core          # Core library (pure stdlib, no dependencies)
pip install -e ".[dev]"        # Desktop/server + dev tools
```

## Usage

### Web Viewer

```bash
# Serve a .scoda package
scoda-serve --package mydata.scoda

# Or via python module
python -m scoda_engine.serve --package mydata.scoda
```

Opens a web viewer at `http://localhost:8080` with manifest-driven tables, trees, charts, detail modals, and search.

### MCP Server (for LLM integration)

```bash
# stdio mode (for Claude Desktop)
scoda-mcp --package mydata.scoda

# SSE mode (integrated with web server on /mcp/)
scoda-serve --package mydata.scoda
# MCP available at http://localhost:8080/mcp/sse
```

### GUI Control Panel

```bash
python -m scoda_engine.gui
```

Tkinter-based control panel with package selection, server start/stop, and log viewer.

### PyInstaller Build

```bash
python scripts/build.py
```

Produces `ScodaDesktop.exe` (GUI) and `ScodaMCP.exe` (MCP stdio).

## Testing

```bash
pytest tests/
```

## Project Structure

```
scoda-engine/
├── core/                       # scoda-engine-core (PyPI: pip install scoda-engine-core)
│   ├── pyproject.toml          # Zero dependencies, pure stdlib
│   └── scoda_engine_core/
│       ├── __init__.py         # Public API re-exports
│       └── scoda_package.py    # Core: .scoda ZIP, DB access, PackageRegistry
├── scoda_engine/               # Desktop/server package
│   ├── scoda_package.py        # Backward-compat shim → scoda_engine_core
│   ├── app.py                  # FastAPI web server + API endpoints
│   ├── mcp_server.py           # MCP server (stdio + SSE modes)
│   ├── gui.py                  # Tkinter GUI control panel
│   ├── serve.py                # Server launcher (uvicorn)
│   ├── templates/              # Generic viewer HTML
│   └── static/                 # Generic viewer CSS/JS
├── scripts/                    # Build, release, validation tools
└── tests/                      # Runtime + MCP tests
```

## License

MIT
