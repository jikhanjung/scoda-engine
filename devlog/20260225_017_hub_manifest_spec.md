# Hub Manifest Spec 문서 작성

**Date:** 2026-02-25
**Type:** Documentation

---

## 작업 내용

### 1. Hub Manifest 스펙 문서 신규 작성

**파일:** `docs/HUB_MANIFEST_SPEC.md`

P15 설계 문서(`devlog/20260224_P15_scoda_hub_static_registry.md`)에 흩어져 있던
Hub Manifest 스키마 정보를 독립적인 레퍼런스 문서로 정리.

문서 구성:
1. Overview — Hub의 3가지 JSON 스키마 개요, .scoda 내부 manifest와의 역할 분리, SHA-256 이중 구조
2. Hub Manifest (per-package) — 필드 정의, dependencies 형식, download_url 처리
3. Hub Index (`index.json`) — 루트/패키지/버전 엔트리 스키마
4. 수집 전략과 Hub Manifest의 역할 — Strategy 1 (manifest 파싱) / Strategy 2 (fallback) 비교
5. Sources (`hub/sources.json`) — 수집 대상 repo 스키마
6. 수집 워크플로우 — 처리 순서, 트리거, 스크립트 사용법
7. 클라이언트 동작 — fetch, compare, resolve, download API
8. Hub Manifest 생성 가이드 — 패키지 빌더용 코드 예시 + release.yml 설정
9. 향후 확장 예약 필드

### 2. Hub Manifest는 선택 사항임을 명시

Fallback(Strategy 2)이 manifest 없이도 동작하므로, Hub Manifest가 **선택 사항**임을 문서에 명확히 기술.
전략별 데이터 비교 테이블과 Fallback의 제약 사항 3가지를 추가:
- SHA-256 검증 불가
- 의존성 자동 해결 불가
- 메타데이터(제목, 설명, 라이선스) 누락

### 3. Manifest 파일명에 버전 포함으로 변경

파일명 규칙을 `{package_id}.manifest.json` → `{package_id}-{version}.manifest.json`으로 변경.
`.scoda` 파일명 규칙(`{id}-{version}.scoda`)과 일관성 확보.

변경 파일:
- `docs/HUB_MANIFEST_SPEC.md` — 파일명 규칙, filename 필드 설명, 생성 가이드 코드 예시
- `devlog/20260224_P15_scoda_hub_static_registry.md` — 스키마 설명, 멀티 패키지 릴리스 예시, 빌드 코드 예시

수집 스크립트(`generate_hub_index.py`)는 `*.manifest.json` 패턴으로 매칭하므로 코드 변경 불필요.

### 4. HANDOFF.md에 참조 추가

`docs/HANDOFF.md`의 Key Document References 테이블에 `Hub Manifest spec | docs/HUB_MANIFEST_SPEC.md` 항목 추가.

---

## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `docs/HUB_MANIFEST_SPEC.md` | **신규** — Hub Manifest 스펙 문서 |
| `docs/HANDOFF.md` | 참조 테이블에 항목 추가 |
| `devlog/20260224_P15_scoda_hub_static_registry.md` | manifest 파일명 규칙 버전 포함으로 수정 |
