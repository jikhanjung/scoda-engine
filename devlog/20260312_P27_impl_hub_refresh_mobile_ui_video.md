# P27 구현: Hub Refresh + 모바일 반응형 UI + Animation 동영상

**날짜**: 2026-03-12

## 개요

P27 계획의 우선순위 1~3번 항목을 구현했다.

1. Hub Refresh 버튼
2. 모바일 반응형 UI (햄버거 메뉴)
3. Animation → 동영상 다운로드

## 1. Hub Refresh 버튼

### Web Viewer (Server 모드)

- Navbar에 ↻ 버튼 추가 (`#hub-refresh-btn`)
- 클릭 시 `POST /api/hub/sync` 호출 → 서버가 Hub에서 새 패키지 다운로드
- 새 패키지가 있으면 자동 페이지 리로드
- Desktop 모드에서는 `engine_name` 판별로 버튼 숨김 (엔드포인트 없으므로)

### Desktop GUI (Tkinter)

- Controls 섹션에 "↻ Check Hub" 버튼 추가 (항상 표시)
- 기존 `_fetch_hub_index()`를 백그라운드 스레드로 재실행
- Hub 상태 바는 결과가 있을 때만 표시되지만, Check Hub 버튼은 항상 접근 가능

### 수정 파일

- `scoda_engine/templates/index.html` — navbar에 refresh 버튼
- `scoda_engine/static/js/app.js` — `hubRefresh()` 함수, Desktop 모드 숨김 로직
- `scoda_engine/static/css/style.css` — 버튼 스타일, 동기화 중 spin 애니메이션
- `scoda_engine/gui.py` — Controls에 Check Hub 버튼, `_on_hub_refresh()` 메서드

## 2. 모바일 반응형 UI

### 구현

- `index.html`에 햄버거 토글 버튼 추가 (`#hamburger-toggle`)
- CSS `@media (max-width: 768px)` 미디어 쿼리:
  - 햄버거 버튼 표시
  - `.view-tabs`를 세로 드롭다운으로 전환 (flex-direction: column)
  - 탭 레이블 항상 표시 (hover 불필요)
  - 활성 탭에 좌측 파란 보더 강조
  - 검색바 축소 (180px), 키보드 단축키 힌트 숨김
  - 검색 결과 드롭다운 폭 축소 (320px)
- JS 토글 핸들러:
  - 탭 클릭 시 메뉴 자동 닫힘
  - 외부 클릭 시 메뉴 닫힘
  - 아이콘 ☰ ↔ ✕ 전환

### 수정 파일

- `scoda_engine/templates/index.html` — 햄버거 버튼 요소
- `scoda_engine/static/css/style.css` — 반응형 스타일
- `scoda_engine/static/js/app.js` — `initHamburger()` IIFE

## 3. Animation 동영상 다운로드

### 구현

Morph controls 바에 Record 버튼 (⏺) 추가. 브라우저에 따라 두 가지 방식 자동 분기.

#### Chrome/Edge/Firefox — 오프라인 프레임 방식

- `webm-writer@1.0.0` CDN 라이브러리 사용
- 고정 30fps로 전체 프레임을 순차 렌더링
- `renderMorphFrame(t)` → `writer.addFrame(canvas)` → `writer.complete()` → WebM 다운로드
- PC 성능과 무관하게 매끄러운 영상 생성
- 5프레임마다 UI yield (`setTimeout(r, 0)`)

#### Safari — 실시간 MediaRecorder 방식

- `canvas.captureStream(30)` + `MediaRecorder` API
- 0.5x 속도로 재생하여 stutter 최소화
- WebM 또는 MP4 (브라우저 지원 포맷 자동 선택)

#### 공통 사항

- **해상도**: 1920x1080 고정 (canvas 임시 리사이즈)
- **배경**: 흰색 (`_recordBg` 플래그 → `renderMorphFrame` 내부에서 clearRect 후 fillRect)
- **자동 fit**: 양쪽 트리(base + compare)의 전체 노드 bounding box 계산 → 패딩 120px → 캔버스 중앙에 fit
- 녹화 완료 후 원래 canvas 크기/DPR/transform 자동 복원
- 녹화 중 버튼 빨간 깜빡임 애니메이션

### 수정 파일

- `scoda_engine/templates/index.html` — webm-writer CDN 스크립트 태그
- `scoda_engine/static/js/app.js` — Record 버튼 UI, `recordOffline()`, `recordRealtime()`, `setupRecordCanvas()`, `restoreCanvas()`
- `scoda_engine/static/js/tree_chart.js` — `renderMorphFrame()`에 `_recordBg` 흰색 배경 지원
- `scoda_engine/static/css/style.css` — Record 버튼 스타일, `record-pulse` 애니메이션

## 테스트

- 303 tests 통과 (변경 없음)
- 프론트엔드 변경이므로 기존 백엔드 테스트에 영향 없음

## 남은 P27 항목

- P27-4: Admin Backend — Profile 관리 서버 (설계 검토 필요, 도메인 의존성 높음)
