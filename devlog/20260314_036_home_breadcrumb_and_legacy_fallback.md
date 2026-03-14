# Home 브레드크럼 + Legacy API Fallback + 헤더 버전

**Date**: 2026-03-14

## 변경 사항

### 1. Home 브레드크럼 헤더

`index.html` 네비게이션 바를 `🏠 SCODA / PackageName v0.1.0` 형태로 변경:
- 집 아이콘(`bi-house-door-fill`) + "SCODA" 텍스트 — Home 링크
- `/` 구분자 — 패키지가 없으면 숨김
- 패키지명 + 버전 — 현재 패키지

### 2. GUI 헤더 버전 표시

`gui.py` 파란색 헤더에 `SCODA Desktop v{version}` 표시 (기존에는 타이틀바에만 있었음).

### 3. Legacy `/api/...` Fallback Router

P29(Multi-Package Serving)에서 모든 엔드포인트가 `/api/{package}/...` prefix로 이동.
기존 `/api/manifest`, `/api/queries/...` 경로가 동작하지 않는 문제 발생.

**해결**: `legacy_router` (prefix `/api/`)를 추가하여 단일 패키지 모드 및 테스트 호환성 유지.

**중요**: legacy_router를 pkg_router보다 **먼저** `app.include_router()`해야 함.
그렇지 않으면 FastAPI가 `/api/manifest`를 `/api/{package=manifest}/...`로 매칭함.

```python
app.include_router(legacy_router)   # /api/manifest, /api/queries/... (먼저!)
app.include_router(pkg_router)      # /api/{package}/manifest, ... (나중)
```

### 4. Legacy Router 엔드포인트

| 경로 | 설명 |
|------|------|
| `GET /api/manifest` | UI manifest |
| `GET /api/queries` | 쿼리 목록 |
| `GET /api/queries/{name}/execute` | 쿼리 실행 |
| `GET /api/detail/{name}` | 단일 행 조회 |
| `GET /api/composite/{view}` | 복합 상세 뷰 |
| `GET /api/preferences` | 사용자 설정 |

`get_legacy_db()` dependency: active package → registry, 없으면 direct `get_db()` (테스트 모드).

## 수정 파일

- `scoda_engine/templates/index.html` — Home 브레드크럼 마크업
- `scoda_engine/static/js/app.js` — 패키지 없을 때 구분자 숨김
- `scoda_engine/gui.py` — 헤더 버전 표시
- `scoda_engine/app.py` — legacy_router 추가 + 라우터 등록 순서 수정
