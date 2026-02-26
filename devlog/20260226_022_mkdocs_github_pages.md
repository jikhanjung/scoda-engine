# MkDocs + GitHub Pages 다국어 문서 사이트 구축

**Date:** 2026-02-26
**Plan:** P19
**Status:** Done

---

## 작업 요약

SCODA Engine 문서 9개를 MkDocs + Material 테마 기반 다국어(EN/KO) 사이트로 구축.
GitHub Pages에 배포하며, 기존 Hub `index.json` URL과 공존.

## 수행 내역

### 인프라

| 파일 | 작업 | 내용 |
|------|------|------|
| `pyproject.toml` | 수정 | `docs` 의존성 그룹 추가 (`mkdocs>=1.6,<2.0`, `mkdocs-material>=9.5`, `mkdocs-static-i18n>=1.2`) |
| `mkdocs.yml` | 신규 | Material 테마, i18n 접미사 방식, nav 8문서, 제외 2문서, pymdownx 확장 |
| `.github/workflows/pages.yml` | 신규 | MkDocs 빌드 + Hub index.json 생성 + Pages 배포 통합 워크플로우 |
| `.github/workflows/hub-index.yml` | 삭제 | `pages.yml`로 기능 통합 |

### 문서 생성/수정

| 파일 | 작업 |
|------|------|
| `docs/index.md` | 신규 — EN 랜딩 페이지 |
| `docs/index.ko.md` | 신규 — KO 랜딩 페이지 |
| `docs/SCODA_CONCEPT.md` | 수정 — 말미 KO 섹션을 EN으로 번역 |
| `docs/SCODA_CONCEPT.ko.md` | 신규 — KO 번역 |
| `docs/SCODA_Concept_and_Architecture_Summary.ko.md` | 신규 — KO 번역 |
| `docs/SCODA_Stable_UID_Schema_v0.2.ko.md` | 신규 — KO 번역 |
| `docs/SCODA_WHITEPAPER.md` | 수정 — KO→EN 번역 |
| `docs/SCODA_WHITEPAPER.ko.md` | 신규 — KO 원본 보존 |
| `docs/API_REFERENCE.md` | 수정 — KO→EN 번역 |
| `docs/API_REFERENCE.ko.md` | 신규 — KO 원본 보존 |
| `docs/MCP_GUIDE.md` | 수정 — KO→EN 번역 |
| `docs/MCP_GUIDE.ko.md` | 신규 — KO 원본 보존 |
| `docs/HUB_MANIFEST_SPEC.md` | 수정 — KO→EN 번역 |
| `docs/HUB_MANIFEST_SPEC.ko.md` | 신규 — KO 원본 보존 |
| `docs/RELEASE_GUIDE.md` | 수정 — KO→EN 번역 |
| `docs/RELEASE_GUIDE.ko.md` | 신규 — KO 원본 보존 |
| `docs/HANDOFF.md` | 수정 — P18/P19 완료, workflow 참조 변경 |

### 번역 원칙

- 코드 블록, 기술 식별자, API 경로, UID 포맷 등은 원문 유지
- 기술 용어(MCP, SCODA, REST API 등)는 원어 유지
- 섹션 제목, 설명 텍스트, 테이블 셀, 인라인 코멘트만 번역

## 해결한 이슈

| 이슈 | 원인 | 해결 |
|------|------|------|
| `default_language` 경고 | i18n 플러그인에서 deprecated 옵션 | 제거 (`default: true`로 대체) |
| `--strict` 빌드 실패 | MkDocs 2.0 호환 경고가 에러로 승격 | `--strict` 플래그 제거 |
| MkDocs 2.0 비호환 경고 | Material 테마가 MkDocs 2.0 미지원 예고 | `mkdocs>=1.6,<2.0` 상한 고정 |
| 한국어 TOC 앵커 미동작 | MkDocs slugify가 한국어 문자 제거 | INFO 수준, 빌드 무관 (필요시 영문 앵커 교체 가능) |

## 검증 결과

- `pip install -e ".[docs]"` — 설치 성공
- `mkdocs build` — EN + KO 사이트 빌드 성공 (에러 0건)
- `site/index.html` + `site/index.json` 충돌 없이 공존
- `pytest tests/` — 276개 테스트 전체 통과
