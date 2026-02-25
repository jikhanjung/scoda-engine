# SCODA Engine — Project Handoff Document

**Last updated:** 2026-02-25

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

### Test Status

- All 276 tests passing: `pytest tests/` (runtime + MCP + hub_client)
- All fixtures converted to domain-independent generic data
- MCP subprocess tests support `SCODA_DB_PATH` environment variable

### In Progress

- 없음

### Recent Session (2026-02-25) Summary

1. **Fix: Hub 업데이트 다운로드 버그**: `resolve_download_order()`에서 이름만 비교하던 것을 버전 비교로 수정
2. **Hub Manifest Spec 문서**: P15 설계 문서에 흩어진 스키마 정보를 `docs/HUB_MANIFEST_SPEC.md`로 정리, manifest 파일명에 버전 포함 규칙으로 변경
3. **Detail view redirect**: 데이터 필드 값에 따라 다른 detail view로 분기하는 기능 추가
4. **P17: Hub Dependency UI**: 패키지 목록에 `[requires: ...]` 표시, 다운로드 전 확인 다이얼로그 (dependency 포함 목록 + 총 크기)
5. **Navbar subtitle**: "Powered by SCODA Desktop v{version}" 동적 표시
6. **Release ZIP 파일명**: 버전 태그 포함하도록 변경
7. **Hub SSL fallback**: 기관 네트워크의 SSL 인증서 검증 실패 대응. Windows 인증서 저장소 통합, `HubSSLError` 예외, GUI fallback 다이얼로그 + 설정 저장 (`ScodaDesktop.cfg`)
8. **P15 후속 (trilobase 측) 완료**: Hub manifest 자동 생성 + release.yml 업로드 연동

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
├── scoda_package.py        # Core: .scoda ZIP, DB access, PackageRegistry, register_path
├── hub_client.py           # Hub: fetch index, compare, download, SSL fallback
└── validate_manifest.py    # Manifest validator/linter (pure functions)

scoda_engine/               # PyPI: scoda-engine v0.1.2 (desktop/server)
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
| Web server (임의 경로) | `python -m scoda_engine.serve --scoda-path /path/to/data.scoda` |
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
| Tree Snapshot design | `docs/Trilobase_Tree_Snapshot_Design_v1.md` |
| Tree Snapshot review | `devlog/20260222_P11_tree_snapshot_design_review.md` |
| SCODA concepts | `docs/SCODA_CONCEPT.md` |
| API reference | `docs/API_REFERENCE.md` |
| MCP guide | `docs/MCP_GUIDE.md` |
| CI workflow | `.github/workflows/test.yml` |
| Release workflow | `.github/workflows/release.yml` |
| Arbitrary path loading (P14) | `devlog/20260224_P14_arbitrary_scoda_path_loading.md` |
| Hub static registry (P15) | `devlog/20260224_P15_scoda_hub_static_registry.md` |
| Hub Manifest spec | `docs/HUB_MANIFEST_SPEC.md` |
| Hub index workflow | `.github/workflows/hub-index.yml` |
| Hub Dependency UI (P17) | `devlog/20260225_P17_hub_dependency_ui.md` |
| Hub SSL fallback | `devlog/20260225_019_hub_ssl_fallback.md` |
