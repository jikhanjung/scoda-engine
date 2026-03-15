# SCODA Engine 개발 기록 요약

**최종 업데이트:** 2026-03-15
**총 문서:** 89개 (작업 로그 56개, 계획 문서 33개)
**개발 기간:** 2026-02-19 ~ 2026-03-15 (25일)

---

## 날짜별 작업 요약

### 2026-02-19 (Day 1) — 프로젝트 로드맵 수립

Trilobase에서 추출한 scoda-engine 독립 저장소의 향후 작업 로드맵 수립.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P01 | 계획 | Future Work Roadmap | `20260219_P01_future_roadmap.md` |

4개 마일스톤 정의: S-1 (테스트 fixture 범용화), S-2 (PyPI 배포), S-3 (validate_manifest 중복 제거), S-4 (SCODA Back-office 웹 도구).

---

### 2026-02-20 (Day 2) — 테스트 Fixture 범용화 + 배포 전략 설계

도메인 독립적 테스트 fixture 생성, 전체 테스트 마이그레이션, MCP 서브프로세스 테스트 수정, SCODA 배포 전략 설계.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P02 | 계획 | S-1 Step 1 Plan — Generic Fixture (의존성 없는 테스트) | `20260220_P02_S1_step1_plan.md` |
| P03 | 계획 | S-1 Step 2 Plan — Full Generic Fixture (의존성 포함) | `20260220_P03_S1_step2_plan.md` |
| P04 | 계획 | MCP 서브프로세스 테스트 수정 계획 | `20260220_P04_fix_mcp_subprocess_tests.md` |
| P05 | 계획 | SCODA Distribution and Architecture Strategy | `20260220_P05_SCODA_Distribution_and_Architecture_Strategy.md` |
| 001 | 작업 | S-1 Step 1: Generic Fixture Conversion (16 클래스, 189 테스트) | `20260220_001_S1_step1_generic_fixture.md` |
| 002 | 작업 | S-1 Step 2: Full Conversion + release.py 범용화 (~1,183줄 삭제) | `20260220_002_S1_step2_generic_fixture_complete.md` |
| 003 | 작업 | MCP 서브프로세스 테스트 수정 (`SCODA_DB_PATH` 환경변수) | `20260220_003_fix_mcp_subprocess_tests.md` |

**결과:** `generic_db`, `generic_client`, `generic_dep_db` fixture 생성. `conftest.py` 1,975→792줄. 196 tests passing.

---

### 2026-02-21 (Day 3) — Core 패키지 분리 + 버전 관리 전략

`scoda-engine-core`를 독립 패키지로 분리 (monorepo `core/` 구조). 버전 관리 전략 수립.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P06 | 계획 | scoda-engine-core Separation Plan (10단계) | `20260221_P06_core_separation_plan.md` |
| P07 | 계획 | Version Management Strategy (독립 SemVer, Git 태그) | `20260221_P07_version_management_strategy.md` |
| 004 | 작업 | S-2: scoda-engine-core 분리 구현 + backward-compat shim | `20260221_004_S2_core_separation.md` |

**결과:** `scoda_package.py`를 `core/scoda_engine_core/`로 이동. `sys.modules` shim으로 하위 호환. 196 tests passing.

---

### 2026-02-22 (Day 4) — Spec 정합성 + validate_manifest 중복 제거 + Tree Snapshot 검토

SCODA 스펙과 런타임 코드의 5개 갭 해소, validate_manifest를 core로 이동, Boolean 라벨 통일, Tree Snapshot 설계 검토.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P08 | 계획 | S-5 SCODA Package Spec Alignment (5개 갭) | `20260222_P08_scoda_spec_alignment.md` |
| P09 | 계획 | S-3 validate_manifest Deduplication Plan | `20260222_P09_validate_manifest_dedup_plan.md` |
| P10 | 계획 | Trilobase validate_manifest Cleanup (trilobase 측) | `20260222_P10_trilobase_validate_manifest_cleanup.md` |
| P11 | 계획 | Tree Snapshot Design v1 Review (2-layer 아키텍처 제안) | `20260222_P11_tree_snapshot_design_review.md` |
| 005 | 작업 | S-3: validate_manifest 중복 제거 (core로 이동) | `20260222_005_S3_validate_manifest_dedup.md` |
| 006 | 작업 | S-5: SCODA Spec Alignment (checksum, SemVer range, dependency) | `20260222_006_S5_scoda_spec_alignment.md` |
| 007 | 작업 | Boolean 표시 라벨 통일 (`true_label`/`false_label`) | `20260222_007_fix_boolean_label_defaults.md` |

**결과:** Checksum-on-load, SemVer range 파싱, dependency 검증, 예외 클래스 3개 추가. 225 tests passing.

---

### 2026-02-23 (Day 5) — CI/CD + UI 개선

GitHub Actions CI/CD 파이프라인, Manual Release 워크플로우, label_map 동적 컬럼 라벨, Navbar 구조 변경.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P12 | 계획 | GitHub Actions CI 테스트 자동화 (2 OS × 2 Python) | `20260223_P12_github_actions_ci.md` |
| P13 | 계획 | Manual Release 워크플로우 (PyInstaller 빌드 + GitHub Release) | `20260223_P13_manual_release_workflow.md` |
| 008 | 작업 | S-6: label_map 동적 컬럼 라벨 (`renderLinkedTable`) | `20260223_008_S6_label_map_dynamic_column.md` |
| 009 | 작업 | S-7: GitHub Actions CI 구현 (`test.yml`) | `20260223_009_S7_github_actions_ci.md` |
| 010 | 작업 | Manual Release 워크플로우 구현 (`release.yml`) | `20260223_010_manual_release_workflow.md` |
| 011 | 작업 | Navbar Title 구조 변경 (패키지명 메인, SCODA Desktop 서브) | `20260223_011_navbar_title_restructure.md` |

**결과:** `.github/workflows/test.yml`, `release.yml` 생성. label_map으로 행 데이터 기반 동적 헤더 지원.

---

### 2026-02-24 (Day 6) — 임의 경로 로딩 + SCODA Hub 구현

`.scoda` 파일의 임의 경로 로딩, SCODA Hub 정적 레지스트리 인프라 구축, Hub 클라이언트 + GUI 통합, 버전 업 + 버그 수정.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P14 | 계획 | 임의 경로 .scoda 패키지 로딩 (`register_path`, CLI, GUI, 환경변수) | `20260224_P14_arbitrary_scoda_path_loading.md` |
| P15 | 계획 | SCODA Hub 정적 레지스트리 설계 (GitHub Pages + Releases) | `20260224_P15_scoda_hub_static_registry.md` |
| P16 | 계획 | Hub 패키지 자동 체크 및 다운로드 (`hub_client.py` + GUI) | `20260224_P16_hub_package_auto_check_download.md` |
| 012 | 작업 | 임의 경로 .scoda 로딩 구현 (Core + CLI + GUI + env) | `20260224_012_arbitrary_scoda_path_loading.md` |
| 013 | 작업 | Hub 인덱스 인프라 (`sources.json`, `generate_hub_index.py`, Actions) | `20260224_013_hub_index_infrastructure.md` |
| 014 | 작업 | Hub 클라이언트 + GUI 통합 (fetch/compare/download/resolve) | `20260224_014_hub_client_and_gui.md` |
| 015 | 작업 | Desktop v0.1.2 버전 업 (Hub 기능 포함, Open File/D&D 제거) | `20260224_015_desktop_v0.1.2.md` |
| 016 | 작업 | Fix: Hub 업데이트 다운로드 버전 비교 버그 | `20260224_016_fix_hub_update_download.md` |

**결과:** Hub 정적 레지스트리 완성 (index.json 자동 생성, GUI 다운로드). Desktop v0.1.2. 255 tests passing.

---

### 2026-02-25 (Day 7) — Hub 고도화 + SSL 대응 + EXE 아이콘

Hub Manifest 스펙 문서화, Navbar 버전 표시, 기관 네트워크 SSL fallback, EXE/GUI 윈도우 아이콘 적용.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P17 | 계획 | Hub Dependency UI + 다운로드 확인 다이얼로그 | `20260225_P17_hub_dependency_ui.md` |
| 017 | 작업 | Hub Manifest Spec 문서 + 파일명에 버전 포함 규칙 | `20260225_017_hub_manifest_spec.md` |
| 018 | 작업 | Navbar "Powered by SCODA Desktop v{version}" 동적 표시 | `20260225_018_navbar_powered_by.md` |
| 019 | 작업 | Hub SSL Fallback (Windows 인증서 저장소, HubSSLError, 설정 저장) | `20260225_019_hub_ssl_fallback.md` |
| 020 | 작업 | EXE 및 GUI 윈도우 아이콘 적용 (멀티 사이즈 ICO) | `20260225_020_exe_window_icon.md` |

**결과:** SSL 인증서 검증 실패 대응 (기관 프록시). `ScodaDesktop.cfg` 설정 저장. 멀티 사이즈 ICO 아이콘. 276 tests passing.

---

### 2026-02-26 (Day 8) — 포트 설정 + MkDocs + Hub 파일명 정리

Hyper-V 포트 충돌 대응 (GUI 포트 설정/자동 탐색), MkDocs + Material 테마로 다국어 문서 사이트 구축, Hub index 파일명 변경.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P18 | 계획 | GUI 서버 포트 설정 및 자동 탐색 | `20260226_P18_configurable_server_port.md` |
| P19 | 계획 | MkDocs + GitHub Pages 다국어 문서 사이트 구축 | `20260226_P19_mkdocs_github_pages.md` |
| 021 | 작업 | GUI 서버 포트 설정 및 자동 탐색 (P18) | `20260226_021_configurable_server_port.md` |
| 022 | 작업 | MkDocs + GitHub Pages 다국어 문서 사이트 구축 (P19) | `20260226_022_mkdocs_github_pages.md` |
| 023 | 작업 | Hub index 파일명 변경 (index.json → scoda-hub-index.json) | `20260226_023_hub_index_filename_rename.md` |

**결과:** Hyper-V 포트 충돌 해소 (자동 탐색 + 설정 저장). EN/KO 다국어 문서 사이트 빌드 성공. Hub index 파일명을 `scoda-hub-index.json`으로 변경하여 MkDocs와의 충돌 해소. 276 tests passing.

---

### 2026-02-28 (Day 10) — Radial Hierarchy Display 설계

Hierarchy 뷰에 방사형(radial) 트리 display mode를 추가하는 계획 문서 작성. D3.js lazy load, Canvas+SVG 렌더링, semantic LOD, 줌/검색/detail 연동 설계.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P20 | 계획 | Radial Hierarchy Display Mode (D3.js, Canvas+SVG, LOD) | `20260228_P20_radial_hierarchy_display.md` |

---

### 2026-03-01 (Day 11) — Radial Tree 고도화 + CRUD 프레임워크 + Global Controls

P20 radial tree 구현 후 대폭 개선, 잘못된 .scoda 에러 처리, manifest-driven global controls 프레임워크, Preferences API(overlay DB), manifest-driven CRUD 프레임워크 구현.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P21 | 계획 | CRUD 프레임워크 계획 (entity_schema + crud_engine + REST API) | `20260301_P21_crud_backend_plan.md` |
| 024 | 작업 | Radial Tree 기능 고도화 (버그 수정, pruned tree, collapse, subtree, 컨텍스트 메뉴) | `20260301_024_radial_tree_enhancements.md` |
| 025 | 작업 | 잘못된 .scoda 파일 에러 처리 (BadZipFile → ValueError 변환) | `20260301_025_fix_invalid_scoda_error_handling.md` |
| 026 | 작업 | Global Controls 프레임워크 (manifest-driven 드롭다운, 쿼리 자동 병합) | `20260301_026_global_controls_framework.md` |
| 027 | 작업 | Preferences API (overlay DB 저장, localStorage 제거) | `20260301_027_preferences_api.md` |
| 028 | 작업 | Manifest-Driven CRUD Framework (entity_schema, crud_engine, 27개 테스트) | `20260301_028_crud_framework.md` |

**결과:** Radial tree에 collapse/expand, subtree, 컨텍스트 메뉴 추가. Admin/Viewer 모드 분리. CRUD REST API 10개 엔드포인트. 303 tests passing.

---

### 2026-03-02 (Day 12) — 프로덕션 Docker 배포 + Tree Chart 이중 레이아웃

프로덕션 웹 뷰어 Docker 환경 구축, Hub 패키지 빌드 타임 자동 다운로드, nginx+app 단일 컨테이너 통합, Tree Chart radial+rectangular 이중 레이아웃.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P22 | 계획 | 프로덕션 웹 뷰어 Docker 배포 (nginx + gunicorn + Docker Compose) | `20260302_P22_production_web_viewer.md` |
| P23 | 계획 | Tree Chart Layout Mode (radial + rectangular, 용어 정리) | `20260302_P23_tree_chart_layout_mode.md` |
| 029 | 작업 | 프로덕션 웹 뷰어 구현 (serve_web.py, /healthz, MCP opt-in, deploy/) | `20260302_029_production_web_viewer.md` |
| 030 | 작업 | Docker 빌드 시 Hub 패키지 자동 다운로드 (fetch_packages.py) | `20260302_030_docker_hub_auto_fetch.md` |
| 031 | 작업 | nginx + app 단일 Docker 이미지 (2-컨테이너 → 1-컨테이너) | `20260302_031_single_container_docker.md` |
| 032 | 작업 | Tree Chart — Radial + Rectangular Layout Mode (radial.js → tree_chart.js) | `20260302_032_tree_chart_rectangular_layout.md` |

**결과:** Docker Hub `honestjung/scoda-server:0.1.0` 게시. GCP 서버 배포 완료. Tree Chart에 rectangular cladogram 레이아웃 추가. 303 tests passing.

---

### 2026-03-03 (Day 13) — Tree Chart 레이아웃 품질 개선

Rectangular/radial 레이아웃의 겹침 문제 해결을 위해 d3.tree()를 bottom-up 레이아웃 엔진으로 교체. 라벨 위치 분기, rank별 X 정렬.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| 033 | 작업 | Tree Chart Layout Refinements (bottom-up 엔진, 라벨 위치, rank 정렬) | `20260303_033_tree_chart_layout_refinements.md` |

**결과:** Bottom-up 레이아웃으로 leaf 겹침 원천 방지. Radial/rectangular 모두 동일 원리 적용. Desktop v0.1.5.

---

### 2026-03-06 (Day 16) — Docker 단순화 + CI Docker Hub + 버전 스크립트

Docker에서 nginx 제거(gunicorn 직접 서빙), 기관 네트워크 SSL 우회, leaf 간격 최적화, Release workflow에 Docker Hub 자동 빌드 추가, 버전 관리 스크립트.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| 034 | 작업 | Docker nginx 제거 — gunicorn 직접 서빙, 포트 8081 | `20260306_034_remove_nginx_from_docker.md` |
| 035 | 작업 | Docker 빌드 SSL 우회 + 프로덕션 엔진 이름 분리 (`SCODA_ENGINE_NAME`) | `20260306_035_docker_ssl_and_engine_name.md` |
| 036 | 작업 | Rectangular Tree leaf 간격 축소 (LEAF_GAP 12→6px) | `20260306_036_tree_leaf_gap_reduction.md` |
| 037 | 작업 | Release workflow에 Docker Hub 빌드·push 추가 | `20260306_037_release_docker_hub.md` |
| 038 | 작업 | `scripts/bump_version.py` 추가 (pyproject.toml + \_\_init\_\_.py 동시 업데이트) | `20260306_038_bump_version_script.md` |

**결과:** Docker 구조 단순화 (nginx 제거). CI에서 자동 Docker Hub 게시. 버전 불일치 방지 스크립트. Desktop v0.1.8.

---

### 2026-03-07 (Day 17) — Side-by-Side Tree Chart (P24)

`tree_chart.js`를 `TreeChartInstance` 클래스로 전면 리팩토링하여 두 개의 독립 트리를 동시 렌더링. Side-by-Side 뷰, Diff Tree 시각화 구현.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P24 | 계획 | Side-by-Side Tree — TreeChartInstance 리팩토링 설계 | `20260307_P24_side_by_side_tree_refactoring.md` |
| 039 | 작업 | TreeChartInstance 클래스 리팩토링 + Side-by-Side 뷰 (v0.2.0) | `20260307_039_side_by_side_tree.md` |
| 040 | 작업 | SBS Sync 보강 (hover/depth/collapse/subtree) + bitmap cache 성능 최적화 | `20260307_040_sbs_sync_and_perf.md` |
| 041 | 작업 | Diff Tree 시각화 (status별 색상, 범례, tooltip, moved re-parent) | `20260307_041_diff_tree.md` |

**결과:** 전역 20+개 변수 → 클래스 인스턴스화. SBS zoom/pan/hover/collapse/depth 5종 동기화. Diff Tree 색상 코딩. Desktop v0.2.0.

---

### 2026-03-09 (Day 19) — Compound View + Animated Morphing (P25)

Compound View 타입(탭 안 서브탭 + 로컬 컨트롤) 도입, 두 프로필 트리 간 모프(morph) 애니메이션, 렌더링 엔진 단순화.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P25 | 계획 | Compound View + Animated Morphing 설계 | `20260309_P25_compound_view_and_morph.md` |
| 042 | 작업 | Compound View 구현 + Morph 애니메이션 + 렌더링 단순화 + UX 개선 | `20260309_042_compound_view_morph_and_ui.md` |

**결과:** `type: compound` manifest 타입 추가. `tree_chart_morph` display 타입. genera_count 쿼리 10,310ms→9ms. Text scale A±/[]키 조절.

---

### 2026-03-11 (Day 21) — Hub 개선 + Tree Search/Watch/Removed (P26)

Hub 인덱스 최신 버전만 포함하도록 변경, Hub 주기적 동기화 API 추가, Tree Chart 검색 버그 수정, Watch 기능, Removed Taxa 패널.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P26 | 계획 | Tree Search 개선 + Watch 기능 + Removed Taxa 목록 설계 | `20260311_P26_tree_search_and_watch.md` |
| P26 구현 | 작업 | P26 구현 전체 (Search 수정, Watch, Removed 패널, morph collapse 버그) | `20260311_P26_impl_tree_search_watch_removed.md` |
| 042 | 작업 | Hub Index: latest 릴리스만 포함 (--all 플래그 제거) | `20260311_042_hub_index_latest_only.md` |
| 043 | 작업 | Hub 주기적 동기화 + 온디맨드 `POST /api/hub/sync` API | `20260311_043_hub_periodic_and_ondemand_sync.md` |
| 044 | 작업 | UI 개선: Show Text 아이콘화, Morph 라벨 각도 보간, Diff legend 위치 수정 | `20260311_044_ui_polish_and_morph_label_fix.md` |

**결과:** Watch 노드 2x 확대 렌더링, 금색 링. Removed Taxa 패널 (클릭 시 zoom). morph collapse 버그 수정. v0.2.3.

---

### 2026-03-12 (Day 22) — Hub Refresh + 모바일 반응형 UI + Animation 동영상 (P27)

서버 재시작 없이 Hub 패키지 갱신, 768px 이하 모바일 햄버거 메뉴, Morph animation WebM 동영상 다운로드.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P27 | 계획 | Admin Backend + Animation Export + Hub Refresh 설계 | `20260312_P27_admin_backend_and_hub_refresh.md` |
| P27 구현 | 작업 | Hub Refresh + 모바일 UI + Animation 동영상 구현 | `20260312_P27_impl_hub_refresh_mobile_ui_video.md` |

**결과:** Navbar ↻ 버튼 + Desktop GUI "Check Hub" 버튼. 768px 이하 햄버거 드롭다운 메뉴. 1920×1080 WebM 오프라인 렌더링 (Chrome/Edge/Firefox) + MediaRecorder (Safari).

---

### 2026-03-13 (Day 23) — 버그 수정 + Tree 기능 강화

Composite detail 엔드포인트 버그 수정, Tree Chart visible depth 슬라이더, 텍스트 크기 단축키, Multi-Package Serving 계획.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P28 | 계획 | 지질시대 + 출판 연도 타임라인 설계 (초안) | `20260313_P28_geologic_time_and_publication_timeline.md` |
| P29 | 계획 | Multi-Package Serving 설계 (URL prefix 기반) | `20260313_P29_multi_package_serving.md` |
| 028 | 작업 | Composite detail 버그 수정 3건 + Tree visible depth 슬라이더 | `20260313_028_composite_bugfix_and_tree_depth_slider.md` |
| 029 | 작업 | Tree 노드 라벨 폰트 크기 단축키 (`[`/`]` 키) | `20260313_029_tree_text_scale_keyboard_shortcut.md` |

**결과:** Composite 쿼리 파라미터 누락 자동 채움. Visible depth 슬라이더(radial/rect/SBS/morph 동기화). `[`/`]` 단축키 0.3~5.0 범위.

---

### 2026-03-14 (Day 24) — Timeline Sub-view (P28) + Multi-Package Serving (P29)

시간축 슬라이더 + morph 연쇄 애니메이션 타임라인 서브뷰, 오프라인 vendor JS 내장, Multi-Package Serving (v0.3.0).

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P28 구현 | 계획 | Timeline 구현 상세 계획 (Phase 1+2) | `20260314_P28_timeline_implementation_plan.md` |
| 030 | 작업 | Timeline Sub-view 구현 (`tree_chart_timeline` 타입, 컨트롤 바, morph 재생) | `20260314_030_timeline_subview_implementation.md` |
| 031 | 작업 | JS/CSS 라이브러리 로컬 내장 (`static/vendor/`, 오프라인 지원) | `20260314_031_vendor_js_bundling.md` |
| 032 | 작업 | Desktop v0.2.5 + bump_version docker-compose 자동화 + source_query_override | `20260314_032_bump_version_docker_and_misc.md` |
| 033 | 작업 | Fix: Timeline 축 전환 시 빈 트리 잔류 버그 (`fullRoot = null`) | `20260314_033_timeline_axis_switch_bugfix.md` |
| 034 | 작업 | Fix: Timeline play 빈 스텝 무한 루프 방지 (`currentIdx` 갱신 보장) | `20260314_034_timeline_empty_step_infinite_loop_fix.md` |
| 035 | 작업 | P29: Multi-Package Serving 구현 (APIRouter, 랜딩 페이지, API_BASE) | `20260314_035_P29_multi_package_serving_impl.md` |
| 036 | 작업 | Home 브레드크럼 + Legacy `/api/...` Fallback Router | `20260314_036_home_breadcrumb_and_legacy_fallback.md` |

**결과:** Timeline 슬라이더 + ⏮◀⏸▶⏭⏩ 컨트롤 + look-ahead 캐싱. D3/Bootstrap/BI 오프라인 내장(755KB). 모든 엔드포인트 `/api/{package}/...` prefix. 랜딩 페이지(D3 force 배경). v0.3.0, 303 tests.

---

### 2026-03-15 (Day 25) — 모바일 UI 추가 개선 (P30)

Landing 페이지 스크롤, Tree 뷰 드로어 패턴, Removed Taxa 패널 접기, Compound View 서브탭 모바일 수정.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P30 | 계획 | 모바일 UI 개선 — Landing 스크롤 + Tree 드로어 | `20260315_P30_mobile_ui_improvements.md` |
| 036 | 작업 | Removed Taxa 패널 접기/펼치기 (헤더 클릭 토글, 상태 유지) | `20260315_036_removed_panel_collapsible.md` |
| 037 | 작업 | Compound View 서브탭 모바일 미표시 수정 (2행 레이아웃 + 가로 스크롤) | `20260315_037_compound_view_mobile_subtabs.md` |

**결과:** Landing `overflow-y: auto`. Tree 드로어 슬라이드인 + backdrop + 항목 선택 시 자동 닫힘. Removed 패널 접기. Compound 서브탭 2행 배치. v0.3.1→v0.3.2.

---

## 주제별 분류

### 1. 테스트 인프라 (S-1, 02-20)

도메인 독립적 generic fixture로 전체 테스트 마이그레이션.

| 날짜 | 내용 |
|------|------|
| 02-20 | `generic_db`/`generic_client` fixture 생성 (categories, items, tags, relations) |
| 02-20 | `generic_dep_db` fixture 생성 (regions, locations, time_periods) |
| 02-20 | `release.py` 범용화 (hardcoded trilobase 참조 제거) |
| 02-20 | MCP 서브프로세스 테스트 수정 (`SCODA_DB_PATH`) |

### 2. Core 패키지 분리 (S-2/S-3, 02-21~02-22)

`scoda-engine-core`를 순수 stdlib 독립 패키지로 추출.

| 날짜 | 내용 |
|------|------|
| 02-21 | `scoda_package.py`를 `core/scoda_engine_core/`로 이동, backward-compat shim |
| 02-21 | 독립 SemVer + Git 태그 (`core-v*`, `desktop-v*`) 전략 수립 |
| 02-22 | `validate_manifest.py`를 core로 이동 (S-3) |

### 3. SCODA Spec 정합성 (S-5, 02-22)

스펙과 런타임 코드 사이의 갭 5건 해소.

| 날짜 | 내용 |
|------|------|
| 02-22 | Checksum-on-load 검증 |
| 02-22 | `required` dependency 필드, SemVer range 파싱 |
| 02-22 | `ScodaDependencyError` 예외, CHANGELOG.md 지원 |

### 4. CI/CD 인프라 (02-23, 03-06)

| 날짜 | 내용 |
|------|------|
| 02-23 | `test.yml` — 2 OS × 2 Python 매트릭스 CI |
| 02-23 | `release.yml` — PyInstaller 빌드 + GitHub Release |
| 03-06 | `release.yml`에 Docker Hub 자동 빌드·push 추가 |
| 03-06 | `bump_version.py` — pyproject.toml + \_\_init\_\_.py + docker-compose 동시 갱신 |

### 5. Desktop UI 기능 (02-22~03-15)

| 날짜 | 내용 |
|------|------|
| 02-22 | Boolean 라벨 통일 (`true_label`/`false_label`, 전역 기본값) |
| 02-23 | `label_map` 동적 컬럼 라벨 (행 데이터 기반 헤더 결정) |
| 02-23 | Navbar 구조 변경 (패키지명 메인 타이틀) |
| 02-25 | Navbar "Powered by SCODA Desktop v{version}" 동적 표시 |
| 02-25 | EXE 및 GUI 윈도우 아이콘 적용 (멀티 사이즈 ICO) |
| 02-26 | GUI 서버 포트 설정 + 자동 탐색 (Hyper-V 포트 충돌 대응) |
| 03-01 | Global Controls 프레임워크 (manifest-driven 드롭다운, 쿼리 자동 병합) |
| 03-01 | Preferences API (overlay DB 저장, localStorage 완전 제거) |
| 03-06 | Docker nginx 제거 → gunicorn 직접 서빙, 포트 8081 |
| 03-06 | `SCODA_ENGINE_NAME` — Desktop/Server 구분 표시 |
| 03-14 | Home 브레드크럼 (🏠 SCODA / PackageName) |
| 03-15 | Compound View 서브탭 모바일 2행 레이아웃 |

### 6. 임의 경로 로딩 (P14, 02-24)

| 날짜 | 내용 |
|------|------|
| 02-24 | `PackageRegistry.register_path()` Core API |
| 02-24 | `--scoda-path` CLI 인수 (serve, mcp, gui) |
| 02-24 | `SCODA_PACKAGE_PATH` 환경변수 |

### 7. SCODA Hub (P15/P16/P17, 02-24~03-11)

정적 패키지 레지스트리 + 자동 다운로드 시스템.

| 날짜 | 내용 |
|------|------|
| 02-24 | `hub/sources.json` + `generate_hub_index.py` (index.json 수집) |
| 02-24 | `hub_client.py` (fetch/compare/download/resolve, 순수 stdlib) |
| 02-24 | GUI Hub 섹션 (백그라운드 체크, 프로그레스 바, SHA-256 검증) |
| 02-25 | Hub Manifest Spec 문서, SSL fallback (기관 프록시 대응) |
| 02-26 | Hub index 파일명 변경 (`scoda-hub-index.json`) |
| 03-11 | Hub Index: latest 버전만 포함 (누적 제거) |
| 03-11 | `POST /api/hub/sync` 온디맨드 API + 주기적 daemon sync |
| 03-12 | Hub Refresh 버튼 (Navbar ↻ + Desktop GUI "Check Hub") |

### 8. 문서 사이트 (P19, 02-26)

MkDocs + Material 테마 기반 다국어(EN/KO) GitHub Pages 문서 사이트.

| 날짜 | 내용 |
|------|------|
| 02-26 | `mkdocs.yml` 설정 (Material 테마, i18n 접미사 방식) |
| 02-26 | 8개 문서 다국어 분리, 랜딩 페이지 |
| 02-26 | `pages.yml` 통합 워크플로우 (MkDocs + Hub index.json 공존) |

### 9. Tree Chart 시각화 엔진 (P20/P23/P24, 02-28~03-15)

Canvas+SVG 기반 고성능 hierarchy 트리 렌더링 엔진의 단계적 발전.

| 날짜 | 내용 |
|------|------|
| 02-28 | P20: Radial hierarchy display 설계 (D3.js, Canvas+SVG, LOD) |
| 03-01 | Radial tree 구현 + pruned tree, collapse/expand, subtree, 컨텍스트 메뉴 |
| 03-02 | P23: `radial.js` → `tree_chart.js` 전환, rectangular cladogram 추가 |
| 03-03 | Bottom-up 레이아웃 엔진으로 교체 (leaf 겹침 원천 방지) |
| 03-06 | Rectangular leaf 간격 최적화 (LEAF_GAP 12→6px) |
| 03-07 | P24: `TreeChartInstance` 클래스 리팩토링 (전역 20+변수 → 인스턴스) |
| 03-07 | Side-by-Side 뷰 + 5종 동기화 (zoom/hover/depth/collapse/subtree) |
| 03-07 | Diff Tree 시각화 (status별 색상, 범례, moved re-parent) |
| 03-09 | Morph animation (snapshotPositions, lerp, look-ahead, 각도 보간) |
| 03-09 | 렌더링 단순화 (SVG label → canvas, bitmap scale, text scale A±) |
| 03-11 | Tree Search 수정 (zoom 좌표 보정, bounding box fit) |
| 03-11 | Watch 기능 (2x 확대 렌더, 금색 링, 패널, SBS sync) |
| 03-11 | Removed Taxa 패널 (diff/morph 모드, 클릭 zoom) |
| 03-13 | Visible depth 슬라이더 (gear 팝업, radial/rect/SBS/morph 동기화) |
| 03-13 | `[`/`]` 단축키 텍스트 크기 조절 |
| 03-14 | Timeline sub-view (`tree_chart_timeline`, 다중 축, 연쇄 morph, look-ahead) |
| 03-14 | Vendor JS/CSS 내장 (D3, Bootstrap, BI → `/static/vendor/`, 오프라인) |
| 03-15 | Removed Taxa 패널 접기/펼치기 (헤더 클릭 토글, 상태 유지) |

### 10. Compound View (P25, 03-09)

하나의 탭 안에 로컬 컨트롤 + 서브탭을 가진 복합 뷰 타입.

| 날짜 | 내용 |
|------|------|
| 03-09 | `type: compound` manifest 타입 + `loadCompoundView()` |
| 03-09 | `tree_chart_morph` display 타입 — Morph animation sub-view |
| 03-14 | `tree_chart_timeline` display 타입 — Timeline sub-view |
| 03-15 | 모바일 서브탭 미표시 수정 (flex-wrap: wrap, 2행 배치) |

### 11. CRUD 프레임워크 (P21, 03-01)

Manifest-driven 제네릭 CRUD 시스템 (Admin/Viewer 모드 분리).

| 날짜 | 내용 |
|------|------|
| 03-01 | `entity_schema.py` (FieldDef, EntitySchema, 입력 검증) |
| 03-01 | `crud_engine.py` (parameterized SQL CRUD, FK 검증, unique 제약, 훅) |
| 03-01 | REST API 10개 엔드포인트 (`/api/entities/*`, `/api/search/*`) |
| 03-01 | 편집 UI (detail Edit/Delete, FK autocomplete, `readonly_on_edit`) |
| 03-01 | 27개 CRUD 테스트 (`test_crud.py`) |

### 12. 프로덕션 Docker 배포 (P22, 03-02~03-06)

읽기 전용 프로덕션 웹 뷰어를 단일 Docker 컨테이너로 배포.

| 날짜 | 내용 |
|------|------|
| 03-02 | `serve_web.py` (gunicorn 팩토리, CLI, MCP opt-in), `/healthz` 엔드포인트 |
| 03-02 | `fetch_packages.py` — Docker 빌드 시 Hub에서 최신 .scoda 자동 다운로드 |
| 03-02 | 2-컨테이너 → 단일 컨테이너 통합 (nginx + gunicorn) |
| 03-06 | nginx 완전 제거 → gunicorn 포트 8081 직접 서빙 |
| 03-06 | Docker 빌드 타임 SSL 우회 (`SCODA_HUB_SSL_VERIFY=0`) |

### 13. Multi-Package Serving (P29, 03-14)

단일 인스턴스에서 여러 .scoda 패키지를 동시 서빙.

| 날짜 | 내용 |
|------|------|
| 03-14 | `APIRouter(prefix="/api/{package}")` — URL prefix 기반 라우팅 |
| 03-14 | `PackageRegistry.register_db()` + `_set_paths_for_testing()` 자동 등록 |
| 03-14 | `GET /api/packages`, `GET /`, `GET /{package}/` 라우트 |
| 03-14 | `landing.html` — D3 force 배경 + 패키지 카드 그리드 |
| 03-14 | `API_BASE = '/api/{package_name}'` 프론트엔드 주입 + `resolveApiUrl()` |
| 03-14 | Legacy `/api/...` fallback router (하위 호환) |

### 14. 모바일 반응형 UI (P27/P30, 03-12~03-15)

| 날짜 | 내용 |
|------|------|
| 03-12 | 768px 이하 햄버거 메뉴 (view-tabs 세로 드롭다운, 외부 클릭 닫힘) |
| 03-15 | Landing `overflow-y: auto` (스크롤 허용) |
| 03-15 | Tree 뷰 드로어 패턴 (tree-panel overlay, 슬라이드인, backdrop, 자동 닫힘) |
| 03-15 | Compound View 서브탭 2행 배치 + 가로 스크롤 |
| 03-15 | Removed Taxa 패널 접기/펼치기 |

### 15. 설계 문서 (미구현)

| 날짜 | 문서 | 주제 | 상태 |
|------|------|------|------|
| 02-19 | P01 | Future Work Roadmap (S-1~S-4) | S-1~S-3 완료, S-4 대기 |
| 02-20 | P05 | SCODA Distribution and Architecture Strategy | 부분 구현 |
| 02-22 | P11 | Tree Snapshot Design v1 Review | 설계 검토 완료, 구현 대기 |

### 16. 버그 수정

| 날짜 | 내용 | 문서 |
|------|------|------|
| 02-24 | Hub 업데이트 다운로드 시 버전 비교 누락 | `20260224_016_fix_hub_update_download.md` |
| 03-01 | 잘못된 .scoda 파일(BadZipFile) 에러 처리 보강 | `20260301_025_fix_invalid_scoda_error_handling.md` |
| 03-11 | Morph animation에서 collapse 시 노드/엣지 안 숨겨지는 문제 | `20260311_P26_impl_tree_search_watch_removed.md` |
| 03-11 | Tree left-click expand 안 되는 문제 (`_children` 체크 순서) | `20260311_P26_impl_tree_search_watch_removed.md` |
| 03-11 | Morph 라벨 각도 갑작스러운 점프 (shortest-path angular interpolation) | `20260311_044_ui_polish_and_morph_label_fix.md` |
| 03-13 | Composite detail 쿼리 파라미터 누락 (`None` 자동 채움) | `20260313_028_composite_bugfix_and_tree_depth_slider.md` |
| 03-14 | Timeline 축 전환 시 빈 트리 잔류 (`fullRoot = null`) | `20260314_033_timeline_axis_switch_bugfix.md` |
| 03-14 | Timeline play 빈 스텝 무한 루프 (`currentIdx` 갱신 보장) | `20260314_034_timeline_empty_step_infinite_loop_fix.md` |

---

## 문서 유형 통계

| 유형 | 접두사 | 개수 | 설명 |
|------|--------|------|------|
| 작업 로그 | `NNN` (숫자) | 56 | 완료된 작업의 상세 기록 |
| 계획 문서 | `PNN` | 33 | 작업 전 설계/계획 (구현 기록 포함) |

## 테스트 수 추이

| 날짜 | 테스트 수 | 주요 변경 |
|------|-----------|-----------|
| 02-20 | 196 | Generic fixture 전환 + MCP 서브프로세스 수정 |
| 02-22 | 225 | Spec alignment 29개 + validate_manifest 테스트 추가 |
| 02-24 | 255 | 임의 경로 로딩 5개 + Hub 클라이언트 25개 추가 |
| 02-25 | 276 | Hub SSL fallback 21개 추가 |
| 03-01 | 303 | CRUD 프레임워크 27개 추가 |
| 03-06~ | 303 | 이후 전 세션 303 유지 (프론트엔드 위주 변경) |

## 버전 이력

| 날짜 | 패키지 | 버전 | 주요 내용 |
|------|--------|------|-----------|
| 02-22 | scoda-engine-core | 0.1.1 | validate_manifest 통합 |
| 02-24 | scoda-engine (Desktop) | 0.1.1 | 임의 경로 로딩 |
| 02-24 | scoda-engine (Desktop) | 0.1.2 | Hub 자동 체크/다운로드 |
| 03-01 | scoda-engine (Desktop) | 0.1.3 | Radial hierarchy display |
| 03-02 | scoda-server (Docker) | 0.1.0 | 프로덕션 Docker 배포 (Docker Hub) |
| 03-03 | scoda-engine (Desktop) | 0.1.5 | Tree Chart bottom-up 레이아웃 |
| 03-06 | scoda-engine (Desktop) | 0.1.7 | Rectangular leaf 간격 최적화 |
| 03-06 | scoda-engine (Desktop) | 0.1.8 | Release workflow Docker Hub 자동화 |
| 03-07 | scoda-engine (Desktop) | 0.2.0 | TreeChartInstance 리팩토링 + SBS 뷰 |
| 03-11 | scoda-engine (Desktop) | 0.2.3 | Watch/Removed 기능 + UI 개선 |
| 03-14 | scoda-engine (Desktop) | 0.2.5 | Timeline sub-view + vendor 내장 |
| 03-14 | scoda-engine (Desktop) | 0.3.0 | Multi-Package Serving |
| 03-15 | scoda-engine (Desktop) | 0.3.1 | 모바일 UI 개선 (Landing + Tree 드로어) |
| 03-15 | scoda-engine (Desktop) | 0.3.2 | Removed 패널 접기 + Compound 모바일 수정 |
