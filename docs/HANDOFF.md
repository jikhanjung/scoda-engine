# SCODA Engine — Project Handoff Document

**Last updated:** 2026-02-21

---

## 1. Current Status

### Completed Milestones

| Milestone | Status | Commit / Doc |
|-----------|--------|--------------|
| Extract scoda-engine as independent repo from Trilobase | Done | `664965b` |
| P01: Future work roadmap | Done | `devlog/20260219_P01_future_roadmap.md` |
| S-1 Step 1: conftest.py generic fixture conversion | Done | `devlog/20260220_P02_S1_step1_plan.md` |
| S-1 Step 2: Full generic fixture conversion + release.py generalization | Done | `8cfa521` |
| MCP subprocess tests generic fixture conversion | Done | `df7c5f8` |
| P05: SCODA distribution strategy and architecture design | Done | `devlog/20260220_P05_*` |
| P06: scoda-engine-core separation plan | Done | `devlog/20260221_P06_core_separation_plan.md` |
| S-2: scoda-engine-core separation | Done | Monorepo `core/` + shim + import migration |

### Test Status

- All tests passing: `pytest tests/` (runtime + MCP)
- All fixtures converted to domain-independent generic data
- MCP subprocess tests support `SCODA_DB_PATH` environment variable

---

## 2. Next Steps (by priority)

### S-3: validate_manifest.py Deduplication

Replace trilobase's copy of `validate_manifest.py` with an import from `scoda-engine-core`.

### S-4: SCODA Back-office

Web-based tool for managing and packaging `.scoda` packages (long-term project).

---

## 3. Key Architecture

### Zero Domain Code Principle

scoda-engine contains no domain-specific code. All domain logic comes from `.scoda` packages.

### 3-DB Architecture

| DB | Role |
|----|------|
| Canonical (main) | Original data inside `.scoda` package |
| Overlay | User annotations and modifications |
| Dependency | Reference DBs connected via ATTACH |

### Manifest-driven UI

- `ui_manifest` table: defines views, detail modals, and actions
- `ui_queries` table: named SQL queries
- `/api/query/<name>`: query execution endpoint
- `/api/composite/<view>?id=N`: multi-query composite response

### MCP Tools

- 7 built-in tools + dynamic tools loaded from `mcp_tools.json` in `.scoda` packages

### Package Layout (Monorepo)

```
core/scoda_engine_core/     # PyPI: scoda-engine-core (pure stdlib, zero deps)
├── __init__.py             # Public API re-exports
└── scoda_package.py        # Core: .scoda ZIP, DB access, PackageRegistry

scoda_engine/               # PyPI: scoda-engine (desktop/server)
├── scoda_package.py        # Backward-compat shim → scoda_engine_core
├── app.py                  # FastAPI web server
├── mcp_server.py           # MCP server (stdio/SSE)
├── gui.py                  # Tkinter GUI
├── serve.py                # uvicorn launcher
├── templates/              # Generic viewer template
└── static/                 # Generic viewer assets
```

---

## 4. Development Setup

### Basic Setup

```bash
git clone <repo-url> scoda-engine
cd scoda-engine
pip install -e ./core
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/
```

### Entry Points

| Purpose | Command |
|---------|---------|
| Web server | `python -m scoda_engine.serve` |
| MCP server | `python -m scoda_engine.mcp_server` |
| GUI | `python launcher_gui.py` |
| PyInstaller build | `python scripts/build.py` |
| Release packaging | `python scripts/release.py` |

### Conventions

- Core library: `from scoda_engine_core import ScodaPackage, get_db`
- Desktop/server modules: `from scoda_engine_core import ...` (absolute)
- External/test imports: `from scoda_engine.app import app`
- Backward-compat shim: `scoda_engine.scoda_package` still works via `sys.modules` redirect
- Subprocess calls: `-m` flag (`python -m scoda_engine.mcp_server`)

---

## 5. Key Document References

| Document | Location |
|----------|----------|
| Project setup and rules | `CLAUDE.md` |
| Future roadmap | `devlog/20260219_P01_future_roadmap.md` |
| Distribution strategy | `devlog/20260220_P05_SCODA_Distribution_and_Architecture_Strategy.md` |
| Core separation plan | `devlog/20260221_P06_core_separation_plan.md` |
| SCODA concepts | `docs/SCODA_CONCEPT.md` |
| API reference | `docs/API_REFERENCE.md` |
| MCP guide | `docs/MCP_GUIDE.md` |
