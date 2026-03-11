# P26 구현: Tree Search 개선 + Watch 기능 + Removed Taxa 목록

**날짜**: 2026-03-11

## 구현 내용

### 1. Search Nodes 수정

**문제**: morph animation 모드에서 검색 시 `zoomToNode()`가 보간 중인 좌표(`node.cx/cy`)를 사용하여 잘못된 위치로 이동.

**수정**:
- Morph 모드에서 검색 시 base + compare 두 트리를 모두 탐색하여 매치 수집
- `zoomToNode()` 호출 전 현재 morph 시점(`_morphT`)의 보간 좌표를 직접 계산하여 노드에 반영
- 일반 모드에서는 기존 로직 유지

### 2. Watch/Unwatch 컨텍스트 메뉴

- 노드 우클릭 시 "Watch" 또는 "Unwatch" 메뉴 항목 추가 (bi-eye / bi-eye-slash 아이콘)
- `watchedNodes` Set<nodeId>으로 상태 관리
- `toggleWatch(nodeId)` 메서드로 토글 처리

### 3. Watch 목록 패널

- 캔버스 우상단 (toolbar 아래, top: 50px)에 Watch 패널 표시
- 금색(#ffc107) 테두리, 노란 헤더
- 각 항목 클릭 시 `zoomToNode()` 호출 (해당 노드로 이동)
- × 버튼으로 unwatch
- 빈 목록이면 패널 자동 제거

### 4. Watch 노드 확대 렌더링

**일반 모드 (`drawNodes`)**:
- Watch 노드: 기본 반지름 × 2 + 금색 링(#ffc107)
- Watch 노드의 parent + children: 기본 반지름 × 1.5
- 라벨: bold + 1.3배 폰트 + 금색(#856404) + 1.5배 offset

**Morph 모드 (`renderMorphFrame`)**:
- 동일한 2x/1.5x 확대 적용
- 금색 링 렌더링

### 5. Removed Taxa 목록

- Diff tree 모드: `_diff_status === 'removed'` 노드 수집
- Morph animation 모드: base에만 존재하고 compare에 없는 노드 수집
- 캔버스 좌하단에 빨간 테두리 패널로 표시
- 각 항목 클릭 시 해당 노드 위치로 zoom
- `load()` 및 `loadMorph()` 완료 시 자동 업데이트

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/static/js/tree_chart.js` | 검색 수정, Watch 전체 기능, Removed 패널, drawNodes/drawLabels/renderMorphFrame 확대 |
| `scoda_engine/static/css/style.css` | `.tc-watch-panel`, `.tc-removed-panel` 및 하위 요소 스타일 |

## 헬퍼 메서드 추가

- `toggleWatch(nodeId)` — watch 토글 + 패널 갱신 + re-render
- `_getWatchNeighborIds()` — watched 노드의 parent + children ID Set 계산
- `_findNodeById(nodeId)` — morph 양쪽 트리 포함 노드 탐색
- `_updateWatchPanel()` — watch 패널 DOM 생성/갱신/제거
- `_updateRemovedPanel()` — removed 패널 DOM 생성/갱신/제거
