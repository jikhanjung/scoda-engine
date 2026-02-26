# P19 — MkDocs + GitHub Pages 다국어 문서 사이트 구축

**Date:** 2026-02-26
**Status:** Done

---

## 배경

SCODA Engine `docs/`에 9개의 고품질 Markdown 문서가 있지만 공개 문서 사이트가 없었음.
MkDocs + Material 테마로 GitHub Pages에 배포하여 사용자/개발자가 접근 가능한 다국어(EN/KO) 문서 사이트를 구축.

## 핵심 제약

1. 기존 `hub-index.yml` GitHub Actions 워크플로우가 GitHub Pages를 사용 중 (Hub `index.json` 호스팅)
   - Hub URL(`https://jikhanjung.github.io/scoda-engine/index.json`) 유지 필수
   - MkDocs 빌드 결과(`site/`)에 Hub `index.json`을 함께 배치하여 통합
   - `index.html`(MkDocs)과 `index.json`(Hub)은 확장자가 다르므로 충돌 없이 공존
2. 영어 기본, 한국어 페이지 제공, 언어 전환 가능

## 기존 문서 언어 분석

| 문서 | 기존 언어 | 처리 |
|------|----------|------|
| `SCODA_CONCEPT.md` | EN (일부 KO 섹션) | EN 정리 + KO 번역 |
| `SCODA_Concept_and_Architecture_Summary.md` | EN | KO 번역 생성 |
| `SCODA_WHITEPAPER.md` | KO | EN 번역 생성 + KO 원본 보존 |
| `API_REFERENCE.md` | KO+EN | EN 번역 생성 + KO 원본 보존 |
| `MCP_GUIDE.md` | KO+EN | EN 번역 생성 + KO 원본 보존 |
| `HUB_MANIFEST_SPEC.md` | KO | EN 번역 생성 + KO 원본 보존 |
| `RELEASE_GUIDE.md` | KO | EN 번역 생성 + KO 원본 보존 |
| `SCODA_Stable_UID_Schema_v0.2.md` | EN | KO 번역 생성 |

## 변경 사항

### 1. 인프라

#### `pyproject.toml` 수정
`[project.optional-dependencies]`에 `docs` 그룹 추가:
```toml
docs = ["mkdocs>=1.6,<2.0", "mkdocs-material>=9.5", "mkdocs-static-i18n>=1.2"]
```
- MkDocs 2.0은 Material 테마와 호환 불가 예고되어 `<2.0` 상한 고정

#### `mkdocs.yml` 신규
- **테마:** Material (다크/라이트 모드 전환, 탭 네비게이션)
- **i18n 플러그인:** `mkdocs-static-i18n` 파일 접미사 방식
  - `page.md` → EN (기본), `page.ko.md` → KO
  - 헤더에 EN/한국어 전환 버튼 자동 생성
- **nav 구조:** Concepts (4개) + Guides (4개)
- **제외 문서:** `HANDOFF.md` (내부용), `Trilobase_Tree_Snapshot_Design_v1.md` (미구현)
- **Markdown 확장:** pymdownx (highlight, superfences, tabbed), admonition, toc permalink

#### `.github/workflows/pages.yml` 신규
기존 `hub-index.yml`을 대체하는 통합 워크플로우:
```
트리거: push(docs/**, mkdocs.yml, hub/**) + schedule(daily) + workflow_dispatch
빌드:
  1. pip install mkdocs mkdocs-material mkdocs-static-i18n
  2. mkdocs build → site/
  3. generate_hub_index.py → site/index.json
  4. upload-pages-artifact + deploy-pages
```
- MkDocs 문서와 Hub index.json이 같은 Pages에서 공존
- Hub URL 하위 호환 유지

#### `.github/workflows/hub-index.yml` 삭제
`pages.yml`로 기능 통합되어 더 이상 불필요.

### 2. 문서

#### 랜딩 페이지 신규 작성
- `docs/index.md` — EN: 프로젝트 소개, Quick Start, 아키텍처 다이어그램, 문서 링크
- `docs/index.ko.md` — KO: 동일 구조 한국어 번역

#### 기존 문서 다국어 분리
한국어 주 문서 5개 → `.ko.md`(원본 보존) + `.md`(영문 번역):
- `SCODA_WHITEPAPER.md` / `.ko.md`
- `API_REFERENCE.md` / `.ko.md`
- `MCP_GUIDE.md` / `.ko.md`
- `HUB_MANIFEST_SPEC.md` / `.ko.md`
- `RELEASE_GUIDE.md` / `.ko.md`

영문 주 문서 3개 → `.md`(원본 유지/정리) + `.ko.md`(한국어 번역):
- `SCODA_CONCEPT.md` / `.ko.md` — 기존 KO 섹션을 EN으로 번역 정리
- `SCODA_Concept_and_Architecture_Summary.md` / `.ko.md`
- `SCODA_Stable_UID_Schema_v0.2.md` / `.ko.md`

#### 번역 원칙
- 코드 블록(SQL, Python, JSON, bash), 기술 식별자, API 경로, UID 포맷 등은 원문 유지
- 한국어→영어: 섹션 제목, 설명, 테이블 셀, 인라인 코멘트 번역
- 영어→한국어: 기술 용어(MCP, SCODA, REST API 등)는 원어 유지, 설명 텍스트 번역

### 3. HANDOFF.md 업데이트
- P18, P19 완료 기록 추가
- Hub index workflow 참조를 `pages.yml`로 변경
- 최근 세션 요약 갱신

## 최종 파일 구조

```
docs/
├── index.md / index.ko.md                              # 랜딩 페이지
├── SCODA_CONCEPT.md / SCODA_CONCEPT.ko.md              # SCODA 개념
├── SCODA_Concept_and_Architecture_Summary.md / ...ko.md # 아키텍처 요약
├── SCODA_WHITEPAPER.md / SCODA_WHITEPAPER.ko.md        # 백서
├── SCODA_Stable_UID_Schema_v0.2.md / ...ko.md          # UID 스키마
├── API_REFERENCE.md / API_REFERENCE.ko.md              # API 레퍼런스
├── MCP_GUIDE.md / MCP_GUIDE.ko.md                      # MCP 가이드
├── HUB_MANIFEST_SPEC.md / HUB_MANIFEST_SPEC.ko.md     # Hub 사양
├── RELEASE_GUIDE.md / RELEASE_GUIDE.ko.md              # 릴리스 가이드
├── HANDOFF.md                                          # (nav 제외)
└── Trilobase_Tree_Snapshot_Design_v1.md                # (nav 제외)
```

## 검증 결과

| 항목 | 결과 |
|------|------|
| `pip install -e ".[docs]"` | MkDocs + Material + i18n 설치 성공 |
| `mkdocs build` | EN + KO 사이트 빌드 성공 (에러 0건) |
| Hub `index.json` 공존 | `site/index.html` + `site/index.json` 충돌 없음 |
| `pytest tests/` | 276개 테스트 전체 통과 |

## 참고

- MkDocs Material 경고: "MkDocs 2.0 is incompatible with Material for MkDocs"
  - 현재 MkDocs 1.6.1 사용 중이므로 영향 없음
  - `pyproject.toml`에서 `mkdocs>=1.6,<2.0`으로 상한 고정하여 자동 업그레이드 방지
- 한국어 `.ko.md` 파일의 TOC 앵커 링크(예: `#개요`, `#설치-및-설정`)는
  MkDocs가 slugify할 때 한국어를 제거하므로 동작하지 않음 (INFO 수준, 빌드 실패 아님)
  - 문서 내용 열람에는 영향 없음. 필요시 TOC 링크를 영문 앵커로 교체 가능
