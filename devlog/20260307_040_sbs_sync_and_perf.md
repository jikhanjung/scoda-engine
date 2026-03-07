# 040: Side-by-Side Tree — Sync 보강 + 성능 최적화

**날짜:** 2026-03-07
**Related:** 039 (Side-by-Side Tree 기본 구현)

## 개요

Side-by-Side Tree Chart의 동기화 기능을 대폭 보강하고,
zoom/pan 성능을 최적화했다.

## Sync 보강

### 1. Hover Highlight Sync
- `onMouseMove()`: `hoverNodeId` 변경 감지 → `onHoverSync` 콜백 발동
- `setHoverNode(nodeId)`: 수신 측 메서드 — 하이라이트 링 렌더링
- `drawNodes()`: `hoverNodeId` 일치 노드에 cyan(`#00bcd4`) 링 표시
- `mouseleave` 이벤트: 양쪽 hover 동시 해제

### 2. Depth Toggle Sync
- `onDepthToggleSync` 콜백: genus show/hide 토글 시 발동
- `setDepthHidden(hidden)`: 수신 측 메서드 — 트리 재구성 + 툴바 버튼 상태 동기화

### 3. Collapse/Expand Sync
- `toggleNode()`: `_fromSync` 파라미터로 무한 루프 방지
- `onCollapseSync` 콜백: `(nodeId, collapsed)` 전달
- `setNodeCollapsed(nodeId, collapsed)`: 같은 taxon ID를 찾아 동기화
- `_findNodeById(nodeId)`: 접힌 `_children` 내부까지 탐색

### 4. View-as-Root (Subtree) Sync
- `navigateToSubtree(nodeId, _fromSync)`: subtree 진입 시 양쪽 동기화
- `clearSubtreeRoot(_fromSync)`: 전체 트리 복귀 시 양쪽 동기화
- breadcrumb "All" 클릭, reset 버튼도 동기화 대상

### 5. 양쪽 Tooltip
- 공유 `sbs-tooltip` → 패널별 `sbs-left-tooltip`, `sbs-right-tooltip` 분리
- `_showTooltipForNode(nodeId)`: 수신 측에서 노드 좌표로 tooltip 위치 계산
- hover sync 시 양쪽 패널에 동시에 tooltip 표시

## 성능 최적화

### Bitmap Cache (Zoom)
- `_snapshotCache()`: zoom 시작 시 현재 캔버스를 offscreen canvas에 복사
- zoom 중 (scale 변경 시): 노드/링크/가이드 재계산 없이 bitmap blit만 수행
- zoom 끝: full render로 선명하게 복원
- pan (translate only): full render 유지 (충분히 빠름, 라벨 깨짐 방지)

### SVG 라벨 숨김
- zoom 중 `labelsSvg.style('visibility', 'hidden')`: SVG DOM 조작 0건
- zoom 끝에만 `updateLabels()` 한 번 실행 + `visibility: visible`

### Guide Depth 캐싱
- `_guideDepths`: 가이드라인 depth 값 배열 캐싱
- `invalidateGuideCache()`: `computeLayout()` 호출 시 자동 무효화
- 매 프레임 전체 트리 순회 → 캐시 lookup으로 전환

### Zoom Sync 최적화
- `_setupSbsSync()`: `zoom.transform()` API 대신 `canvas.__zoom` 직접 세팅
- d3 zoom `start`/`end` 이벤트가 상대 인스턴스에서 발동하지 않음
- 양쪽 `_zooming` 상태를 source 측 `start`/`end`에서 함께 관리

### Hover 중복 렌더 방지
- `_zooming` 중 hover 변경 시 `render()` 스킵 (zoom이 이미 매 프레임 렌더 중)

## CSS
- `.sbs-panel`: `overflow: hidden` 추가 — SVG 라벨이 패널 경계 넘어가지 않도록

## 수정 파일

| 파일 | 변경 |
|------|------|
| `static/js/tree_chart.js` | sync 콜백 5종, 성능 최적화 3종, tooltip 분리 |
| `static/css/style.css` | `.sbs-panel` overflow: hidden |
| `templates/index.html` | 패널별 tooltip 요소 분리 |
