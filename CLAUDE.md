# CLAUDE.md — SCODA Engine

## Session Start

At the beginning of each session, read `docs/HANDOFF.md` first to understand the current
project status, in-progress work, and next steps. Key architecture and dev setup are also
documented there.

## Quick Start

This is the **SCODA Engine** runtime — a generic viewer/server for `.scoda` data packages.
It was extracted from the Trilobase project. There is **no domain-specific code** here.

## Project Overview

SCODA Engine provides:
- FastAPI web server with manifest-driven generic viewer
- MCP server for LLM integration (stdio + SSE)
- Tkinter GUI control panel
- `.scoda` ZIP package format support
- PyInstaller standalone build

## Repository Structure

```
scoda-engine/
├── pyproject.toml              # Desktop package metadata + dependencies
├── README.md
├── CLAUDE.md
├── pytest.ini                  # pytest config (testpaths=tests)
├── ScodaDesktop.spec           # PyInstaller build spec
├── launcher_gui.py             # GUI entry point
├── launcher_mcp.py             # MCP entry point
├── core/                       # scoda-engine-core (independent PyPI package)
│   ├── pyproject.toml          # Zero dependencies, pure stdlib
│   └── scoda_engine_core/
│       ├── __init__.py         # Public API re-exports
│       ├── scoda_package.py    # Core: .scoda ZIP, DB access, PackageRegistry
│       └── validate_manifest.py # Manifest validator/linter (pure functions)
├── scoda_engine/               # Desktop/server package
│   ├── __init__.py
│   ├── scoda_package.py        # Backward-compat shim → scoda_engine_core
│   ├── app.py                  # FastAPI web server
│   ├── mcp_server.py           # MCP server (stdio/SSE)
│   ├── gui.py                  # Tkinter GUI
│   ├── serve.py                # uvicorn launcher
│   ├── templates/index.html    # Generic viewer template
│   └── static/{css,js}/        # Generic viewer assets
├── scripts/
│   ├── build.py                # PyInstaller EXE builder
│   ├── validate_manifest.py    # Manifest validator CLI (thin wrapper → core)
│   ├── init_overlay_db.py      # Overlay DB initializer
│   └── release.py              # Release packager
├── examples/genus-explorer/    # Example SPA
├── tests/
│   ├── conftest.py             # Shared fixtures
│   ├── test_runtime.py         # Runtime tests
│   ├── test_mcp.py             # MCP integration tests
│   └── test_mcp_basic.py       # MCP basic test
└── docs/                       # SCODA documentation
```

## Key Architecture

- **Zero domain code**: All domain logic comes from `.scoda` packages
- **Monorepo with core separation**: `scoda_engine_core` (pure stdlib) + `scoda_engine` (desktop/server)
- **Manifest-driven UI**: Views, detail modals, and actions defined in DB `ui_manifest`
- **Named queries**: SQL in `ui_queries` table, executed via `/api/query/<name>`
- **Composite detail**: `/api/composite/<view>?id=N` assembles multi-query responses
- **MCP tools**: Built-in (7) + dynamic from `mcp_tools.json` in `.scoda` package
- **3-DB architecture**: canonical (main) + overlay (user annotations) + dependency (ATTACH)

## Testing

```bash
pip install -e ./core
pip install -e ".[dev]"
pytest tests/
```

Test fixtures use trilobase-style sample data but test **SCODA mechanisms** (manifest rendering, query execution, CORS, composite detail, etc.), not domain logic.

## Conventions

- Core library imports: `from scoda_engine_core import ScodaPackage, get_db`
- Desktop/server internal imports: `from scoda_engine_core import ...` (not relative)
- External/test imports use absolute (`from scoda_engine.app import app`)
- Backward-compat shim: `scoda_engine.scoda_package` still works via `sys.modules` redirect
- Subprocess calls use `-m` flag (`python -m scoda_engine.mcp_server`)
