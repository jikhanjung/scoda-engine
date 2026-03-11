# P26 구현: Tree Search 개선 + Watch 기능 + Removed Taxa 목록

**날짜**: 2026-03-11

## 구현 내용

### 1. Search Nodes 수정

**문제 1**: morph animation 모드에서 검색 시 한쪽 트리만 탐색.

**문제 2**: `zoomToNode()` 좌표 계산이 render의 center offset(`translate(t.x + cx*t.k, t.y + cy*t.k)`)을 고려하지 않아 엉뚱한 위치로 이동.

**수정**:
- Morph 모드에서 검색 시 base + compare 두 트리를 모두 탐색하여 매치 수집
- `zoomToNode()` transform 계산 수정: `.translate(-cx - node.cx, -cy - node.cy)` (center offset 보정)
- 검색 결과가 여러 개일 때 bounding box 기반 fit-zoom (`zoomToFitNodes`) 적용
  - 단일 노드/극소 클러스터 → scale=4, 여러 노드 → padding 100px로 전체 fit
- Morph 모드에서 매치 노드들의 보간 좌표를 `_morphT` 시점으로 계산 후 zoom

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
- 상태 변경 시 동적 갱신: `load()`, `loadMorph()`, `toggleNode()`, `navigateToSubtree()`, `clearSubtreeRoot()`, `_navigateMorphSubtree()`, `_rebuildMorphFromFullTree()`

### 6. 버그 수정

**Left-click expand 안 됨**:
- 원인: collapsed 노드(`children=null`)가 `isLeafByRank()`에서 leaf로 판정 → detail modal 분기로 빠짐
- 수정: `onClick()`에서 `nearest._children` 존재 여부를 leaf 체크보다 먼저 확인

**Morph animation에서 collapse 시 노드/엣지 안 숨겨짐**:
- 원인: `renderMorphFrame()`이 `_morphAllNodeIds` + position map을 직접 순회하여 `node._children` 반영 안 됨. `_drawMorphLabels()`만 `this.root.each()` 사용하여 라벨만 사라짐
- 수정: morph 렌더링 시작 시 양쪽 트리의 collapsed 하위 자손 ID를 `collapsedHidden` Set으로 수집, 엣지/노드 루프에서 skip

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/static/js/tree_chart.js` | 검색 수정, zoom 좌표 수정, zoomToFitNodes, Watch 전체 기능, Removed 패널 동적 갱신, morph collapse 처리, expand 버그 수정 |
| `scoda_engine/static/css/style.css` | `.tc-watch-panel`, `.tc-removed-panel` 및 하위 요소 스타일 |

## 추가된 메서드

- `zoomToFitNodes(nodes)` — 노드 배열의 bounding box에 맞는 fit-zoom
- `toggleWatch(nodeId)` — watch 토글 + 패널 갱신 + re-render
- `_getWatchNeighborIds()` — watched 노드의 parent + children ID Set 계산
- `_findNodeById(nodeId)` — morph 양쪽 트리 포함 노드 탐색
- `_updateWatchPanel()` — watch 패널 DOM 생성/갱신/제거
- `_updateRemovedPanel()` — removed 패널 DOM 생성/갱신/제거
