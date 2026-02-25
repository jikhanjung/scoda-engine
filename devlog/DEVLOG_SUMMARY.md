# SCODA Engine 개발 기록 요약

**최종 업데이트:** 2026-02-25
**총 문서:** 35개 (작업 로그 18개, 계획 문서 17개)
**개발 기간:** 2026-02-19 ~ 2026-02-25 (7일)

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

### 2026-02-25 (Day 7) — Hub 고도화 + SSL 대응

Hub Manifest 스펙 문서화, Dependency UI, Navbar 버전 표시, 기관 네트워크 SSL fallback 구현.

| # | 유형 | 제목 | 문서 |
|---|------|------|------|
| P17 | 계획 | Hub Dependency UI + 다운로드 확인 다이얼로그 | `20260225_P17_hub_dependency_ui.md` |
| 017 | 작업 | Hub Manifest Spec 문서 + 파일명에 버전 포함 규칙 | `20260225_017_hub_manifest_spec.md` |
| 018 | 작업 | Navbar "Powered by SCODA Desktop v{version}" 동적 표시 | `20260225_018_navbar_powered_by.md` |
| 019 | 작업 | Hub SSL Fallback (Windows 인증서 저장소, HubSSLError, 설정 저장) | `20260225_019_hub_ssl_fallback.md` |

**결과:** SSL 인증서 검증 실패 대응 (기관 프록시). `ScodaDesktop.cfg` 설정 저장. 276 tests passing.

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

### 4. CI/CD 인프라 (02-23)

| 날짜 | 내용 |
|------|------|
| 02-23 | `test.yml` — 2 OS × 2 Python 매트릭스 CI |
| 02-23 | `release.yml` — PyInstaller 빌드 + GitHub Release |

### 5. Generic Viewer 기능 (02-22~02-23)

| 날짜 | 내용 |
|------|------|
| 02-22 | Boolean 라벨 통일 (`true_label`/`false_label`, 전역 기본값) |
| 02-23 | `label_map` 동적 컬럼 라벨 (행 데이터 기반 헤더 결정) |
| 02-23 | Navbar 구조 변경 (패키지명 메인 타이틀) |
| 02-25 | Navbar "Powered by SCODA Desktop v{version}" 동적 표시 |

### 6. 임의 경로 로딩 (P14, 02-24)

| 날짜 | 내용 |
|------|------|
| 02-24 | `PackageRegistry.register_path()` Core API |
| 02-24 | `--scoda-path` CLI 인수 (serve, mcp, gui) |
| 02-24 | `SCODA_PACKAGE_PATH` 환경변수 |

### 7. SCODA Hub (P15/P16/P17, 02-24~02-25)

정적 패키지 레지스트리 + 자동 다운로드 시스템.

| 날짜 | 내용 |
|------|------|
| 02-24 | `hub/sources.json` + `generate_hub_index.py` (index.json 수집) |
| 02-24 | `hub-index.yml` (GitHub Actions → Pages 배포) |
| 02-24 | `hub_client.py` (fetch/compare/download/resolve, 순수 stdlib) |
| 02-24 | GUI Hub 섹션 (백그라운드 체크, 프로그레스 바, SHA-256 검증) |
| 02-24 | Hub 업데이트 버전 비교 버그 수정 |
| 02-25 | Hub Manifest Spec 문서 (`docs/HUB_MANIFEST_SPEC.md`) |
| 02-25 | Dependency UI (`[requires: ...]`) + 다운로드 확인 다이얼로그 |
| 02-25 | SSL fallback (Windows 인증서 저장소, `HubSSLError`, 설정 저장) |

### 8. 설계 문서 (미구현)

| 날짜 | 문서 | 주제 | 상태 |
|------|------|------|------|
| 02-19 | P01 | Future Work Roadmap (S-1~S-4) | S-1~S-3 완료, S-4 대기 |
| 02-20 | P05 | SCODA Distribution and Architecture Strategy | 부분 구현 |
| 02-22 | P11 | Tree Snapshot Design v1 Review | 설계 검토 완료, 구현 대기 |

### 9. 버그 수정

| 날짜 | 내용 | 문서 |
|------|------|------|
| 02-24 | Hub 업데이트 다운로드 시 버전 비교 누락 | `20260224_016_fix_hub_update_download.md` |

---

## 문서 유형 통계

| 유형 | 접두사 | 개수 | 설명 |
|------|--------|------|------|
| 작업 로그 | `NNN` (숫자) | 18 | 완료된 작업의 상세 기록 |
| 계획 문서 | `PNN` | 17 | 작업 전 설계/계획 |

## 테스트 수 추이

| 날짜 | 테스트 수 | 주요 변경 |
|------|-----------|-----------|
| 02-20 | 196 | Generic fixture 전환 + MCP 서브프로세스 수정 |
| 02-22 | 225 | Spec alignment 29개 + validate_manifest 테스트 추가 |
| 02-24 | 255 | 임의 경로 로딩 5개 + Hub 클라이언트 25개 추가 |
| 02-25 | 276 | Hub SSL fallback 21개 추가 |

## 버전 이력

| 날짜 | 패키지 | 버전 | 주요 내용 |
|------|--------|------|-----------|
| 02-22 | scoda-engine-core | 0.1.1 | validate_manifest 통합 |
| 02-24 | scoda-engine (Desktop) | 0.1.1 | 임의 경로 로딩 |
| 02-24 | scoda-engine (Desktop) | 0.1.2 | Hub 자동 체크/다운로드 |
