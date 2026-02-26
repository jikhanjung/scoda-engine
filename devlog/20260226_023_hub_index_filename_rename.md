# Hub Index 파일명 변경: index.json → scoda-hub-index.json

**Date:** 2026-02-26
**Status:** Done

---

## 작업 요약

GitHub Pages 루트(`https://jikhanjung.github.io/scoda-engine/`)에 접근 시
`index.json`이 노출되어 MkDocs 문서 사이트(`index.html`)와 혼동되는 문제 해결.
Hub index 파일명을 `scoda-hub-index.json`으로 변경하여 브라우저 기본 접근 시
MkDocs 문서가 표시되도록 함.

## 수행 내역

### 코드/설정 변경 (5파일)

| 파일 | 변경 내용 |
|------|-----------|
| `core/scoda_engine_core/hub_client.py:25` | `DEFAULT_HUB_URL` → `.../scoda-hub-index.json` |
| `scripts/generate_hub_index.py` | `INDEX_PATH`, `--output` 기본값, docstring, help 텍스트, dry-run 레이블 업데이트 |
| `.github/workflows/pages.yml:47` | `--output site/scoda-hub-index.json` |
| `.gitignore:20` | `hub/index.json` → `hub/scoda-hub-index.json` |
| `tests/test_hub_client.py` | 테스트 URL 내 `index.json` → `scoda-hub-index.json` (7곳) |

### 문서 변경 (2파일)

| 파일 | 변경 내용 |
|------|-----------|
| `docs/HUB_MANIFEST_SPEC.md` | 섹션 제목, URL, 워크플로우 다이어그램, 처리 순서 업데이트 |
| `docs/HUB_MANIFEST_SPEC.ko.md` | 동일 (한국어 버전) |

devlog는 작성 당시의 기록이므로 수정하지 않음.

## 검증

- `pytest tests/` — 276 테스트 전체 통과
