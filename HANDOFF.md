# SCODA Engine — Project Handoff Document

**Last updated:** 2026-03-01

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
| P14: 임의 경로 .scoda 패키지 로딩 | Done | `devlog/20260224_012_arbitrary_scoda_path_loading.md` |
| Desktop v0.1.1 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |
| P15: SCODA Hub 정적 레지스트리 (scoda-engine 측) | Done | `devlog/20260224_P15_scoda_hub_static_registry.md` |
| P16: Hub 패키지 자동 체크 및 다운로드 | Done | `devlog/20260224_014_hub_client_and_gui.md` |
| Desktop v0.1.2 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |
| P15 후속: trilobase Hub manifest 연동 | Done | trilobase 측 완료 |
| Fix: Hub 업데이트 다운로드 버전 비교 버그 | Done | `devlog/20260224_016_fix_hub_update_download.md` |
| Hub Manifest Spec 문서 + 파일명 규칙 변경 | Done | `devlog/20260225_017_hub_manifest_spec.md` |
| Detail view redirect (데이터 필드 기반 뷰 분기) | Done | `8bf93f6` |
| P17: Hub Dependency UI + 다운로드 확인 다이얼로그 | Done | `devlog/20260225_P17_hub_dependency_ui.md` |
| Navbar subtitle 엔진 버전 동적 표시 | Done | `devlog/20260225_018_navbar_powered_by.md` |
| Release ZIP 파일명에 버전 태그 포함 | Done | `1aedc79` |
| Hub SSL fallback (기관 네트워크 대응) | Done | `devlog/20260225_019_hub_ssl_fallback.md` |
| P18: GUI 서버 포트 설정 및 자동 탐색 | Done | `devlog/20260226_P18_configurable_server_port.md` |
| P19: MkDocs + GitHub Pages 다국어 문서 사이트 | Done | `devlog/20260226_P19_mkdocs_github_pages.md` |
| P20: Radial hierarchy display mode | Done | `devlog/20260228_P20_radial_hierarchy_display.md` |
| Desktop v0.1.3 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |
| Global controls (profile selector) | Done | `devlog/20260301_026_global_controls_framework.md` |
| Preferences API (overlay persistence) | Done | `devlog/20260301_027_preferences_api.md` |
| P21: Manifest-driven CRUD framework | Done | `devlog/20260301_028_crud_framework.md` |

### Test Status

- All 303 tests passing: `pytest tests/` (runtime 218 + MCP 7 + hub_client 24 + CRUD 27 + etc.)
- All fixtures converted to domain-independent generic data
- MCP subprocess tests support `SCODA_DB_PATH` environment variable
- CRUD tests: `tests/test_crud.py` (27 tests) — generic item/category fixture

### In Progress

- 없음

### Recent Session (2026-03-01) Summary

1. **P21: Manifest-Driven CRUD Framework**: manifest의 `editable_entities` 섹션 기반 제네릭 CRUD 엔진. `entity_schema.py` (FieldDef/EntitySchema 파서), `crud_engine.py` (parameterized SQL, FK 검증, unique 제약, post-mutation 훅), REST 엔드포인트 10개, admin/viewer 모드 분리, `--db-path`/`--mode` CLI 인자. 프론트엔드: Edit/Delete/Add 버튼, FK autocomplete (name 표시 + 검색), `readonly_on_edit`, PLACED_IN rank 필터링. `validate_manifest.py`에 editable_entities 검증 규칙 추가. 27개 테스트.

---

## 2. Next Steps (by priority)

### Tree Snapshot 설계 심화 (P11 후속)

`design/Trilobase_Tree_Snapshot_Design_v1.md`의 설계를 구체화.
검토 결과 tree opinion 패턴은 SCODA 범용 메커니즘으로 설계 가능.
후속 검토 항목: `devlog/20260222_P11_tree_snapshot_design_review.md` Section 7 참조.

주요 미결 항목:
- 2-layer API 경계 (범용 framework + 도메인 plugin)
- Resolve 알고리즘 설계
- 기존 manifest/overlay와의 통합 시나리오
- Phase 0 POC 범위 확정

### S-4: SCODA Back-office (partially done)

P21 CRUD framework가 기반 작업 완료. 남은 항목:
- MCP 서버에 CRUD 도구 등록 (현재 보류)
- Overlay 기반 편집 (.scoda 불변 유지)
- `.scoda` 빌드 버튼 (편집 완료 후 패키징)
- ScodaDesktop GUI에 admin 모드 노출 (현재 CLI 전용)

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
- Generic viewer supports: hierarchy (tree/nested_table/radial), table, detail modal, global search, annotations
- Boolean columns: customizable via `true_label`/`false_label`, defaults `BOOLEAN_TRUE_LABEL`/`BOOLEAN_FALSE_LABEL`
- `label_map` 동적 컬럼 label: 행 데이터의 특정 필드 값에 따라 테이블 헤더를 동적으로 결정 (혼합 시 fallback)
- `editable_entities`: admin 모드에서 CRUD UI 자동 생성 (FK autocomplete, readonly_on_edit, post-mutation hooks)
- `global_controls`: 전역 파라미터 셀렉터 (profile 등), overlay DB에 사용자 선택 저장

### MCP Tools

- 7 built-in tools + dynamic tools loaded from `mcp_tools.json` in `.scoda` packages

### Package Layout (Monorepo)

```
core/scoda_engine_core/     # PyPI: scoda-engine-core v0.1.1 (pure stdlib, zero deps)
├── __init__.py             # Public API re-exports
├── scoda_package.py        # Core: .scoda ZIP, DB access, PackageRegistry, register_path
├── hub_client.py           # Hub: fetch index, compare, download, SSL fallback
└── validate_manifest.py    # Manifest validator/linter (pure functions)

scoda_engine/               # PyPI: scoda-engine v0.1.3 (desktop/server)
├── scoda_package.py        # Backward-compat shim → scoda_engine_core
├── app.py                  # FastAPI web server (+ CRUD endpoints)
├── entity_schema.py        # P21: FieldDef/EntitySchema parser + validation
├── crud_engine.py          # P21: Generic CRUD engine (FK, constraints, hooks)
├── mcp_server.py           # MCP server (stdio/SSE)
├── gui.py                  # Tkinter GUI
├── serve.py                # uvicorn launcher (--db-path, --mode admin|viewer)
├── templates/              # Generic viewer template
└── static/                 # Generic viewer assets (+ radial.js for D3 radial tree)
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
| Web server (임의 경로) | `python -m scoda_engine.serve --scoda-path /path/to/data.scoda` |
| Web server (admin 편집) | `python -m scoda_engine.serve --db-path /path/to/data.db --mode admin` |
| MCP server | `python -m scoda_engine.mcp_server` |
| GUI | `python launcher_gui.py` |
| GUI (임의 경로) | `python launcher_gui.py --scoda-path /path/to/data.scoda` |
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
| Tree Snapshot design | `design/Trilobase_Tree_Snapshot_Design_v1.md` |
| Tree Snapshot review | `devlog/20260222_P11_tree_snapshot_design_review.md` |
| SCODA concepts | `design/SCODA_CONCEPT.md` |
| API reference | `docs/API_REFERENCE.md` |
| MCP guide | `docs/MCP_GUIDE.md` |
| CI workflow | `.github/workflows/test.yml` |
| Release workflow | `.github/workflows/release.yml` |
| Arbitrary path loading (P14) | `devlog/20260224_P14_arbitrary_scoda_path_loading.md` |
| Hub static registry (P15) | `devlog/20260224_P15_scoda_hub_static_registry.md` |
| Hub Manifest spec | `docs/HUB_MANIFEST_SPEC.md` |
| Docs + Hub Pages workflow | `.github/workflows/pages.yml` |
| Hub Dependency UI (P17) | `devlog/20260225_P17_hub_dependency_ui.md` |
| Hub SSL fallback | `devlog/20260225_019_hub_ssl_fallback.md` |
| Radial hierarchy display (P20) | `devlog/20260228_P20_radial_hierarchy_display.md` |
| Global controls framework | `devlog/20260301_026_global_controls_framework.md` |
| Preferences API | `devlog/20260301_027_preferences_api.md` |
| CRUD framework (P21) | `devlog/20260301_028_crud_framework.md` |
