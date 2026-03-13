# 032 — 버전 0.2.5 + bump_version 개선 + source_query_override

**날짜**: 2026-03-14

## 변경 내용

### 1. 버전 0.2.5

Desktop v0.2.4 → v0.2.5. P28 timeline 서브뷰 + vendor 내장 포함.

### 2. bump_version.py — docker-compose 자동 업데이트

`scripts/bump_version.py`의 `VERSION_FILES`에 `deploy/docker-compose.yml` 추가.
`image: honestjung/scoda-server:X.Y.Z` 태그를 자동 갱신.

기존에는 docker-compose 이미지 태그를 수동으로 별도 수정해야 했음.

### 3. source_query_override — 축 모드별 쿼리 교체

P28 timeline 서브뷰에서 축 모드(지질시대 / 출판 연도)마다 다른 source_query를 사용해야 하는 경우를 위해,
`timeline_options.axis_modes[].source_query_override`와 `edge_query_override` 지원 추가.

`loadAxis()`에서 모드 전환 시 서브뷰의 `source_query` / `tree_chart_options.edge_query`를 동적으로 교체.

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scripts/bump_version.py` | docker-compose.yml 패턴 추가 |
| `deploy/docker-compose.yml` | 이미지 태그 0.2.3 → 0.2.5 |
| `pyproject.toml` | 0.2.4 → 0.2.5 |
| `scoda_engine/__init__.py` | 0.2.4 → 0.2.5 |
| `scoda_engine/static/js/app.js` | `loadAxis()`에 override 로직 추가 |

## 테스트

- 303 tests 통과
