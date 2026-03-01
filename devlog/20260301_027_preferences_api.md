# 026: Global Controls → Overlay DB 저장

**날짜**: 2026-03-01

## 배경

P79에서 구현한 global controls(profile selector 등) 사용자 선택값이 `localStorage`에 저장되어 브라우저 의존적이었음. 다른 브라우저에서 열면 설정이 초기화되는 문제.

## 변경 사항

### Backend: `scoda_engine/app.py`

- CORS `allow_methods`에 `PUT` 추가
- Preferences API 엔드포인트 3개 추가 (catch-all 라우트 앞):
  - `GET /api/preferences` — 전체 preference 조회 (`pref_*` 키)
  - `GET /api/preferences/{key}` — 단일 값 조회
  - `PUT /api/preferences/{key}` — 값 저장 (`INSERT OR REPLACE`)
- `overlay.overlay_metadata` 테이블 재사용 (key prefix: `pref_`)

### Frontend: `scoda_engine/static/js/app.js`

- `loadManifest()`: `localStorage.getItem` → `GET /api/preferences` 일괄 로드
- `renderGlobalControls()`: `localStorage.setItem` → `PUT /api/preferences/{key}` fire-and-forget
- `localStorage` 참조 완전 제거

## 검증

- 기존 테스트 223개 전체 통과
- 수동 검증: `curl localhost:8000/api/preferences`
- DB 확인: `sqlite3 *_overlay.db "SELECT * FROM overlay_metadata WHERE key LIKE 'pref_%'"`
