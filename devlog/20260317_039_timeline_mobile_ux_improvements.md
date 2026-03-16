# Timeline & Mobile UX 개선

**날짜:** 2026-03-17
**작업 유형:** UI/UX 개선

---

## 배경

Timeline 컴파운드 뷰와 트리 차트 툴바의 모바일 사용성 문제를 개선했다.

---

## 변경 내용

### 1. Timeline 컨트롤 레이아웃 개선 (`style.css`)

- 하단 컨트롤 패널 위치 상향: `bottom: 16px` → `32px` (데스크톱), `8px` → `20px` (모바일)
  - 슬라이더 하단이 잘리는 문제 수정
- 시대명 레이블 폭 고정: `min-width: 80px` → `width: 120px` → `width: 80px` + `text-overflow: ellipsis`
  - 시대명 길이 변화에 따라 다른 컨트롤 위치가 흔들리는 문제 수정
- 컨트롤 2행 구조로 재편:
  - 1행: 재생 버튼들 + 현재 시대명 + step 카운터 + 속도 셀렉터
  - 2행: 슬라이더 (전체 폭)
- 역재생 버튼 (`tl-play-rev-btn`) 제거

### 2. Timeline axis 모드 → compound sub-tab으로 승격 (`app.js`)

- 기존: Timeline 서브뷰 내 캔버스 위에 소형 탭 버튼으로 axis 선택
- 변경: Comparison 뷰의 Diff Table / Diff Tree와 동일한 레벨의 compound-sub-tab으로 표시
- 구현 방식:
  - `loadCompoundView()`에서 `tree_chart_timeline` display + `axis_modes.length > 1`이면 axis마다 별도 탭 생성 (composite key: `${sk}__axis${i}`)
  - `switchCompoundSubView()`에서 composite key 파싱 → `realSubKey` + `axisIdx` 분리
  - `renderCompoundTimelineSubView(subKey, subView, containerEl, initialAxisIdx)`로 시그니처 변경
  - 내부 axis 탭 HTML/JS 전부 제거
  - `default_sub_view`가 원본 키를 가리키면 자동으로 첫 번째 composite 키로 매핑

### 3. 트리 툴바 버튼 모바일 정리 (`tree_chart.js`, `style.css`)

- 기어(⚙) 팝업을 항상 렌더링 (기존: `_rankOrder.length > 1` 조건부)
- 팝업에 Layout 섹션, Text size 섹션 추가 (`.tc-popup-layout`, `.tc-popup-text`)
- 데스크톱: 팝업 내 해당 섹션 숨김 (`display: none`)
- 모바일: 툴바의 레이아웃 버튼 + 폰트 버튼 숨기고 팝업 섹션만 표시
- 레이아웃/텍스트 버튼 이벤트를 `querySelectorAll`로 변경 → 툴바+팝업 양쪽 동시 바인딩
- `switchLayout()`도 `querySelectorAll`로 업데이트

### 4. 모바일 검색 입력창 가변 폭 (`style.css`)

- `width: 180px` 고정 → `width: 180px; max-width: 30vw; min-width: 80px`
- 좁은 화면에서 자동 축소

---

## 영향 범위

- `scoda_engine/static/js/app.js`
- `scoda_engine/static/js/tree_chart.js`
- `scoda_engine/static/css/style.css`
