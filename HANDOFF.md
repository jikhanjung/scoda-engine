# SCODA Engine — Project Handoff Document

**Last updated:** 2026-03-14

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
| Radial tree 고도화 (subtree view, context menu) | Done | `devlog/20260301_024_radial_tree_enhancements.md` |
| Fix: 잘못된 .scoda 파일 BadZipFile 에러 처리 | Done | `devlog/20260301_025_fix_invalid_scoda_error_handling.md` |
| Desktop v0.1.4 버전 업 | Done | `62b736e` |
| Global controls (profile selector) | Done | `devlog/20260301_026_global_controls_framework.md` |
| Preferences API (overlay persistence) | Done | `devlog/20260301_027_preferences_api.md` |
| P21: Manifest-driven CRUD framework | Done | `devlog/20260301_028_crud_framework.md` |
| P22: Production web viewer (Docker deploy) | Done | `devlog/20260302_P22_production_web_viewer.md` |
| Collapsible view tab labels | Done | `9cc7c2d` |
| P23: Tree chart — radial + rectangular layout | Done | `devlog/20260302_P23_tree_chart_layout_mode.md` |
| Desktop v0.1.5 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |
| Docker nginx 제거, gunicorn 직접 서빙 | Done | `devlog/20260306_034_remove_nginx_from_docker.md` |
| Docker SSL 우회 + 엔진 이름 표시 | Done | `devlog/20260306_035_docker_ssl_and_engine_name.md` |
| Rectangular tree leaf 간격 축소 | Done | `devlog/20260306_036_tree_leaf_gap_reduction.md` |
| Desktop v0.1.6 ~ v0.1.9 버전 업 | Done | Docker Hub CI, bump_version 스크립트 등 |
| CI: Release workflow Docker Hub 빌드·push | Done | `devlog/20260306_037_release_docker_hub.md` |
| bump_version 스크립트 추가 | Done | `devlog/20260306_038_bump_version_script.md` |
| Compare mode UI (toggle, row color) | Done | `c4063f5` |
| P24: Side-by-Side Tree (TreeChartInstance 리팩토링) | Done | `devlog/20260307_P24_side_by_side_tree_refactoring.md` |
| Side-by-Side Tree — 듀얼 렌더링 + zoom/layout 동기화 | Done | `devlog/20260307_039_side_by_side_tree.md` |
| Side-by-Side sync 보강 + 성능 최적화 | Done | `devlog/20260307_040_sbs_sync_and_perf.md` |
| Diff Tree 시각화 (색상, 범례, 툴팁, moved re-parent) | Done | `devlog/20260307_041_diff_tree.md` |
| Desktop v0.2.0 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |
| P26: Tree Search 수정 + Watch 기능 + Removed Taxa 목록 | Done | `devlog/20260311_P26_impl_tree_search_watch_removed.md` |
| P27: Hub Refresh + 모바일 반응형 UI + Animation 동영상 다운로드 | Done | `devlog/20260312_P27_impl_hub_refresh_mobile_ui_video.md` |
| Composite detail bugfix + Tree chart visible depth slider | Done | `devlog/20260313_028_composite_bugfix_and_tree_depth_slider.md` |
| Tree 노드 라벨 폰트 크기 단축키 (`[`/`]` 키) | Done | `devlog/20260313_029_tree_text_scale_keyboard_shortcut.md` |
| P28: Timeline sub-view (지질시대/출판연도 타임라인) | Done | `devlog/20260314_030_timeline_subview_implementation.md` |
| Vendor JS/CSS 번들링 (오프라인 지원) | Done | `devlog/20260314_031_vendor_js_bundling.md` |
| Desktop v0.2.4 ~ v0.2.5 버전 업 | Done | `e7ab362`, `915acd6` |
| Fix: Timeline 축 전환 시 빈 트리 처리 | Done | `devlog/20260314_033_timeline_axis_switch_bugfix.md` |
| Fix: Timeline play 빈 스텝 무한 루프 방지 | Done | `devlog/20260314_034_timeline_empty_step_infinite_loop_fix.md` |
| P29: Multi-Package Serving | Done | `devlog/20260314_035_P29_multi_package_serving_impl.md` |
| Desktop v0.3.0 버전 업 | Done | `scoda_engine/__init__.py`, `pyproject.toml` |

### Test Status

- All 303 tests passing: `pytest tests/` (runtime 218 + MCP 7 + hub_client 24 + CRUD 27 + etc.)
- All fixtures converted to domain-independent generic data
- MCP subprocess tests support `SCODA_DB_PATH` environment variable
- CRUD tests: `tests/test_crud.py` (27 tests) — generic item/category fixture
- Tests use `/api/test/...` URL prefix (package name "test" registered by `_set_paths_for_testing`)

### In Progress

- 없음

### Recent Sessions (2026-03-12 ~ 2026-03-14) Summary

**2026-03-14: P29 Multi-Package Serving + GUI 개선**
1. **APIRouter 리팩토링**: 모든 per-package 엔드포인트를 `pkg_router = APIRouter(prefix="/api/{package}")` 로 이동. `Depends(get_package_db)` dependency로 자동 conn lifecycle 관리.
2. **글로벌 엔드포인트**: `GET /api/packages` (패키지 목록), `GET /healthz` (패키지 수 포함), `POST /api/hub/sync` (기존 유지).
3. **페이지 라우트**: `GET /` — 단일 패키지 시 `/{name}/`으로 302 redirect, 복수 패키지 시 `landing.html` 렌더. `GET /{package}/` — 패키지 뷰어.
4. **Frontend `API_BASE`**: `index.html`에 `const API_BASE = '/api/{package_name}'` 주입, `app.js`의 18개 fetch URL을 `${API_BASE}/...`로 교체. `resolveApiUrl()` 유틸로 manifest `view.source` URL 변환.
5. **랜딩 페이지**: `landing.html` — D3 force simulation 배경, 패키지 카드 그리드, 다크 테마.
6. **Home breadcrumb**: navbar에 🏠 SCODA / 패키지명 구조. 홈 아이콘 클릭 시 패키지 목록으로 이동.
7. **serve_web.py**: 디렉토리 모드에서 `set_active_package()` 제거 (모든 패키지 동시 서빙).
8. **Core 변경**: `PackageRegistry.register_db()` 메서드 추가, `_set_paths_for_testing()`에 registry "test" 등록 추가, `check_same_thread=False` 적용.
9. **GUI 개선**: Start Server 패키지 선택 불요 (모든 패키지 동시 서빙), 패키지 목록 정보 표시 전용, 헤더에 버전 표시.
10. **테스트**: 모든 `/api/...` URL → `/api/test/...` 변환, `GET /` 테스트 302 redirect 검증, 303개 전체 통과.
11. **버전 업**: v0.2.5 → v0.3.0

**2026-03-12: P27 구현**
1. **Hub Refresh 버튼**: Web navbar ↻ 버튼 (`POST /api/hub/sync`), Desktop GUI "Check Hub" 버튼, 새 패키지 감지 시 자동 페이지 리로드.
2. **모바일 반응형 UI**: 768px breakpoint, 햄버거 메뉴(☰↔✕), 세로 드롭다운 탭, 검색바·단축키 힌트 숨김.
3. **Animation 동영상 다운로드**: Chrome/Edge/Firefox: 오프라인 30fps `webm-writer` 렌더링, Safari: captureStream + MediaRecorder, 1920×1080 고정, ⏺ 녹화 버튼.

**2026-03-13: 버그 수정 + Tree 기능 강화**
1. **Composite detail bugfix**: `_execute_query()` 누락 파라미터 자동 None 채움, 에러 체크 순서 수정.
2. **Tree visible depth slider**: 기어 아이콘 팝업, rank 기반 depth 제한, Radial/Rect/SBS 동기화.
3. **Text scale 단축키**: `[`/`]` 키로 텍스트 크기 조절 (0.3~5.0 범위).

**2026-03-14: P28 Timeline sub-view**
1. **Timeline sub-view**: `tree_chart_timeline` display type, 다중 axis mode (지질시대/출판연도), 동적 query override.
2. **Timeline playback**: ⏮◀⏸▶⏭⏩ 컨트롤, scrubber 슬라이더, speed selector (0.5x~4x), step 간 morph animation, look-ahead 캐싱.
3. **Vendor JS 번들링**: CDN → `/static/vendor/` (D3, Bootstrap, icons) — Desktop 오프라인 지원.
4. **버그 수정**: 축 전환 시 빈 트리 처리 (`fullRoot = null`), 빈 스텝 무한 루프 방지 (`currentIdx` 증가 보장).

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

### P27-4: Admin Backend — Profile 관리 (보류)

소스 txt 업로드 → 신규 profile 등록, addendum 병합.
기존 P21 CRUD는 개인 overlay 편집으로 유지, admin backend는 canonical DB 직접 편집 모드.
도메인 의존성 복잡도로 인해 보류 중.

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

### Multi-Package Serving (P29)

- All per-package API endpoints: `/api/{package}/...` (APIRouter with prefix)
- Global endpoints: `GET /api/packages`, `GET /healthz`, `POST /api/hub/sync`
- Page routes: `GET /` (landing/redirect), `GET /{package}/` (viewer)
- Frontend: `API_BASE = '/api/{package_name}'` injected by template, `resolveApiUrl()` for manifest source URLs
- `PackageRegistry.register_db()` for testing, `_set_paths_for_testing()` auto-registers as "test"

### Manifest-driven UI

- `ui_manifest` table: defines views, detail modals, and actions
- `ui_queries` table: named SQL queries
- `/api/{package}/queries/<name>/execute`: query execution endpoint
- `/api/{package}/composite/<view>?id=N`: multi-query composite response
- Generic viewer supports: hierarchy (tree/nested_table/tree_chart with radial+rectangular+side-by-side+diff layout), table, detail modal, global search, annotations, compare mode, node watch, removed taxa panel, timeline sub-view
- Tree chart features: visible depth slider, text scale shortcut (`[`/`]`), morph animation video export (WebM)
- Timeline sub-view: `tree_chart_timeline` display type, multiple axis modes, step slider, playback controls, morph between steps, look-ahead caching
- Boolean columns: customizable via `true_label`/`false_label`, defaults `BOOLEAN_TRUE_LABEL`/`BOOLEAN_FALSE_LABEL`
- `label_map` 동적 컬럼 label: 행 데이터의 특정 필드 값에 따라 테이블 헤더를 동적으로 결정 (혼합 시 fallback)
- `editable_entities`: admin 모드에서 CRUD UI 자동 생성 (FK autocomplete, readonly_on_edit, post-mutation hooks)
- `global_controls`: 전역 파라미터 셀렉터 (profile 등), overlay DB에 사용자 선택 저장
- Hub Refresh: 서버 재시작 없이 Hub 패키지 갱신 (`POST /api/hub/sync`)
- Mobile responsive: 768px 이하에서 햄버거 메뉴로 전환

### MCP Tools

- 7 built-in tools + dynamic tools loaded from `mcp_tools.json` in `.scoda` packages

### Package Layout (Monorepo)

```
core/scoda_engine_core/     # PyPI: scoda-engine-core v0.1.1 (pure stdlib, zero deps)
├── __init__.py             # Public API re-exports
├── scoda_package.py        # Core: .scoda ZIP, DB access, PackageRegistry, register_path
├── hub_client.py           # Hub: fetch index, compare, download, SSL fallback
└── validate_manifest.py    # Manifest validator/linter (pure functions)

scoda_engine/               # PyPI: scoda-engine v0.3.0 (desktop/server)
├── scoda_package.py        # Backward-compat shim → scoda_engine_core
├── app.py                  # FastAPI web server (multi-package APIRouter + CRUD)
├── entity_schema.py        # P21: FieldDef/EntitySchema parser + validation
├── crud_engine.py          # P21: Generic CRUD engine (FK, constraints, hooks)
├── mcp_server.py           # MCP server (stdio/SSE)
├── gui.py                  # Tkinter GUI (multi-package serving)
├── serve.py                # uvicorn launcher (--db-path, --mode admin|viewer)
├── serve_web.py            # Production web launcher (gunicorn/Docker)
├── templates/              # index.html (viewer) + landing.html (multi-package)
└── static/                 # Viewer assets (app.js, tree_chart.js, vendor/)
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
| Web server (production) | `python -m scoda_engine.serve_web --scoda-path /path/to/data.scoda` |
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
| Production web viewer (P22) | `devlog/20260302_P22_production_web_viewer.md` |
| Tree chart layout mode (P23) | `devlog/20260302_P23_tree_chart_layout_mode.md` |
| Side-by-Side Tree refactoring (P24) | `devlog/20260307_P24_side_by_side_tree_refactoring.md` |
| Diff Tree 시각화 | `devlog/20260307_041_diff_tree.md` |
| P26: Search + Watch + Removed | `devlog/20260311_P26_impl_tree_search_watch_removed.md` |
| P27 계획 | `devlog/20260312_P27_admin_backend_and_hub_refresh.md` |
| P27 구현 (Hub Refresh, 모바일 UI, 동영상) | `devlog/20260312_P27_impl_hub_refresh_mobile_ui_video.md` |
| Composite bugfix + depth slider | `devlog/20260313_028_composite_bugfix_and_tree_depth_slider.md` |
| Text scale keyboard shortcut | `devlog/20260313_029_tree_text_scale_keyboard_shortcut.md` |
| P28 계획 (Timeline) | `devlog/20260313_P28_geologic_time_and_publication_timeline.md` |
| P28 구현 (Timeline sub-view) | `devlog/20260314_030_timeline_subview_implementation.md` |
| Vendor JS 번들링 | `devlog/20260314_031_vendor_js_bundling.md` |
| Version bump + docker-compose 자동화 | `devlog/20260314_032_bump_version_docker_and_misc.md` |
| Timeline 축 전환 빈 트리 bugfix | `devlog/20260314_033_timeline_axis_switch_bugfix.md` |
| Timeline 빈 스텝 무한 루프 bugfix | `devlog/20260314_034_timeline_empty_step_infinite_loop_fix.md` |
| P29 구현 (Multi-Package Serving) | `devlog/20260314_035_P29_multi_package_serving_impl.md` |
