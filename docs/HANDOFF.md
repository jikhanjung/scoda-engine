# SCODA Engine — Project Handoff Document

**Last updated:** 2026-02-23

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
| P07: Version management strategy | Done | `devlog/20260221_P07_version_management_strategy.md` |
| P08/S-5: SCODA spec alignment | Done | `devlog/20260222_P08_scoda_spec_alignment.md` |
| S-3: validate_manifest dedup | Done | `0bd54ba`, core v0.1.1 |
| P10: trilobase validate_manifest cleanup | Done | trilobase repo에서 완료 |
| Boolean 표시 라벨 통일 | Done | `da362c8` |
| P11: Tree Snapshot Design v1 검토 | Done | `devlog/20260222_P11_tree_snapshot_design_review.md` |
| P12: GitHub Actions CI 테스트 자동화 | Done | `devlog/20260223_P12_github_actions_ci.md` |
| P13: Manual Release 워크플로우 | Done | `devlog/20260223_P13_manual_release_workflow.md` |

### Test Status

- All 225 tests passing: `pytest tests/` (runtime + MCP + S-5)
- All fixtures converted to domain-independent generic data
- MCP subprocess tests support `SCODA_DB_PATH` environment variable

### Recent Session (2026-02-23) Summary

오늘 세션에서 진행한 작업:

1. **P12: GitHub Actions CI 테스트 자동화**: PR/main push 시 pytest 자동 실행 워크플로우 구축 (OS: ubuntu/windows, Python: 3.10/3.12)
2. **P13: Manual Release 워크플로우**: workflow_dispatch 기반 수동 릴리스 — PyInstaller 빌드 → ZIP 아티팩트 → GitHub Release 생성 (OS: ubuntu/windows, Python 3.12)

---

## 2. Next Steps (by priority)

### Tree Snapshot 설계 심화 (P11 후속)

`docs/Trilobase_Tree_Snapshot_Design_v1.md`의 설계를 구체화.
검토 결과 tree opinion 패턴은 SCODA 범용 메커니즘으로 설계 가능.
후속 검토 항목: `devlog/20260222_P11_tree_snapshot_design_review.md` Section 7 참조.

주요 미결 항목:
- 2-layer API 경계 (범용 framework + 도메인 plugin)
- Resolve 알고리즘 설계
- 기존 manifest/overlay와의 통합 시나리오
- Phase 0 POC 범위 확정

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
- Generic viewer supports: hierarchy (tree/nested_table), table, detail modal, global search, annotations
- Boolean columns: customizable via `true_label`/`false_label`, defaults `BOOLEAN_TRUE_LABEL`/`BOOLEAN_FALSE_LABEL`
- `label_map` 동적 컬럼 label: 행 데이터의 특정 필드 값에 따라 테이블 헤더를 동적으로 결정 (혼합 시 fallback)

### MCP Tools

- 7 built-in tools + dynamic tools loaded from `mcp_tools.json` in `.scoda` packages

### Package Layout (Monorepo)

```
core/scoda_engine_core/     # PyPI: scoda-engine-core v0.1.1 (pure stdlib, zero deps)
├── __init__.py             # Public API re-exports
├── scoda_package.py        # Core: .scoda ZIP, DB access, PackageRegistry
└── validate_manifest.py    # Manifest validator/linter (pure functions)

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

### Version Management

- 두 패키지 독립 SemVer: `scoda-engine-core` (PyPI) / `scoda-engine` (Desktop)
- Git 태그: `core-v*` (Core), `desktop-v*` (Desktop)
- 런타임 접근: `from scoda_engine_core import __version__` / `from scoda_engine import __version__`
- 릴리스 시 `pyproject.toml` + `__init__.py`의 `__version__` 동기화 필수

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
| Version management strategy | `devlog/20260221_P07_version_management_strategy.md` |
| Tree Snapshot design | `docs/Trilobase_Tree_Snapshot_Design_v1.md` |
| Tree Snapshot review | `devlog/20260222_P11_tree_snapshot_design_review.md` |
| SCODA concepts | `docs/SCODA_CONCEPT.md` |
| API reference | `docs/API_REFERENCE.md` |
| MCP guide | `docs/MCP_GUIDE.md` |
| CI workflow | `.github/workflows/test.yml` |
| Release workflow | `.github/workflows/release.yml` |
