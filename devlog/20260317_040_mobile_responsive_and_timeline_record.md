# 모바일 반응형 UI 개선 + Timeline 녹화 버튼

**날짜:** 2026-03-17
**작업 유형:** UI/UX 개선, 기능 추가

---

## 배경

모바일(768px 이하)에서 여러 UI 요소의 반응형 문제를 수정하고, Timeline 서브뷰에 동영상 녹화 기능을 추가했다.

---

## 변경 내용

### 1. 모바일 반응형 개선 (`style.css`, `index.html`)

**검색창 줄 내림 방지:**
- `.global-controls-container`: `flex-shrink: 1`, `min-width: 0` — Profile 드롭다운 영역 축소 허용
- `.global-control-label`: 모바일에서 숨김 (`display: none`) — "Profile" 라벨 제거, 드롭다운만 표시
- `.global-control-select`: `max-width: 120px`, `text-overflow: ellipsis`
- `.global-search-container`: `flex-shrink: 1`, `min-width: 0` — 기존 `flex-shrink: 0` 오버라이드
- `.global-search-wrapper`: `min-width: 100px`, `flex-shrink: 1`

**Navbar 축소 허용:**
- `#navbar-engine-info`: 모바일에서 숨김 ("Powered by..." 텍스트)
- `.navbar-brand`: `overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0` — 긴 제목 말줄임
- `.navbar .container-fluid`: `flex-wrap: nowrap; min-width: 0`

**컨트롤 패널 축소 허용:**
- `.morph-controls`: 모바일에서 `max-width: calc(100% - 24px); left: 12px; transform: none`
- `.morph-controls input[type="range"]`: `width: 200px` → `100px`, `flex-shrink: 1`
- `.tl-step-label-display`: 모바일에서 `width: auto; min-width: 40px`
- `.timeline-controls`: `min-width: 0; box-sizing: border-box` 추가

**뷰포트 폭 전파 차단:**
- `.view-container { overflow: hidden }` 추가
- `.view-tabs-bar { max-width: 100vw }` 추가
- `.compound-header`: 모바일에서 `overflow: hidden; padding: 6px 8px`
- `.compound-controls`, `.compound-sub-tabs`: `min-width: 0` 추가

### 2. 설정 팝업 레이아웃 버튼 수정 (`style.css`)

- 문제: 모바일에서 `.tc-toolbar .tc-layout-btn { display: none }`이 팝업 내 버튼까지 숨김
- 수정: `.tc-toolbar > .tc-layout-btn` (직계 자식 선택자)로 변경
- `.tc-settings-popup .tc-layout-btn { display: inline-block }` 명시 추가
- `.tc-settings-popup .tc-text-smaller/.tc-text-larger { display: inline-block }` 추가

### 3. Removed 패널 위치 조정 (`style.css`)

- 항상 왼쪽 배치: `right: 16px` → `left: 16px` (데스크톱/모바일 공통)
- 오른쪽 설정 팝업과 겹치지 않음
- Watch 패널: 모바일에서 `left: 16px; right: auto` (breadcrumb 아래, `top: 40px`)
- Removed 패널: 모바일에서 `top: 40px`

### 4. Animation(morph) 서브뷰 reverse play 버튼 제거 (`app.js`)

- `morph-play-rev-btn` HTML, DOM 참조, 이벤트 리스너 모두 제거
- Rewind(⏮) + Pause(⏸) + Play(▶) + FF(⏭) 구성으로 통일

### 5. Timeline 서브뷰에 동영상 녹화 기능 추가 (`app.js`, `style.css`)

- `#tl-record-btn` 추가 (transport row 끝)
- **Offline 녹화** (Chrome/Firefox): WebMWriter 프레임 단위 렌더링
  - 각 step 간 morph 프레임 + 0.3초 hold
  - 1920×1080 고정 해상도, 30fps
  - 진행 상황 표시 (`Rendering... 3/15`)
  - 완료 시 `timeline-animation.webm` 다운로드
- **Realtime 녹화** (Safari fallback): MediaRecorder 실시간 캡처
- morph 녹화와 동일 패턴: `setupRecordCanvas` → 녹화 → `restoreCanvas`

### 6. 녹화 버튼 아이콘 개선 (`app.js`, `style.css`)

- `bi-record-circle`(동심원) → `bi-circle-fill`(채워진 원)로 변경
- `.record-icon`: 빨간색(`#dc3545`), 작은 크기(`0.6em`)
- 녹화 중: 버튼 배경 빨간색 고정, 아이콘만 흰↔빨강 깜박임 (`record-icon-blink` 애니메이션)
- 기존 버튼 전체 opacity 깜박임(`record-pulse`) 제거

---

## 영향 범위

- `scoda_engine/static/css/style.css`
- `scoda_engine/static/js/app.js`
- `scoda_engine/templates/index.html`
