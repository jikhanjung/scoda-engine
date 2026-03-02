# 032: Tree Chart — Radial + Rectangular Layout Mode

**Date:** 2026-03-02
**Status:** Done
**Related:** P23, P20 (Radial hierarchy display)

## 개요

기존 radial-only 계층 시각화를 범용 tree chart 엔진으로 확장.
Radial + Rectangular 두 가지 레이아웃 모드를 toolbar 토글로 전환 가능.
동시에 파일명/용어를 `radial` -> `tree_chart`로 정리.

## 변경 사항

### 1. `radial.js` -> `tree_chart.js` (삭제 + 신규 생성)

**새 상태 변수:**
- `treeLayoutMode`: `'radial'` | `'rectangular'` (기본: radial)
- `cladoBoundsW`, `cladoBoundsH`: rectangular 레이아웃 전체 범위

**레이아웃 디스패처:**
- `computeLayout(root, view)` — treeLayoutMode에 따라 분기
- `computeRadialLayout()` — 기존 방사형 로직 (변경 없음)
- `computeCladogramLayout()` — 신규 rectangular 레이아웃
  - d3.tree().size([treeH, treeW]) 사용
  - leafCount * 24px 최소 높이, maxDepth * 120px 너비
  - node.cx = depth (수평), node.cy = spread (수직), 원점 중심

**렌더링 분기 (treeLayoutMode 체크):**
- `drawGuideLines()`: radial=동심원, rectangular=수직 dashed 선
- `drawLinks()`: radial=quadratic curve, rectangular=elbow connector
- `updateRadialLabels()`: radial=회전 라벨, rectangular=수평 라벨 (rotation=0)
- `computeFitTransform()`: rectangular은 boundsW/H 기반 스케일링

**Toolbar 확장:**
- Layout 토글: 두 개 버튼 (bi-bullseye=radial, bi-diagram-3=rectangular)
- `switchLayout(mode)`: 모드 전환 + 재레이아웃 + 재렌더

**옵션 키 변경:**
- 모든 `view.radial_display` -> `view.tree_chart_options`
- `tree_chart_options.default_layout` 신규 (초기 레이아웃 모드)

### 2. `index.html`

- `id="view-radial"` -> `id="view-tree-chart"`
- 내부 요소 ID: `radial-*` -> `tc-*` (tc-toolbar, tc-canvas-wrap, tc-canvas, tc-labels, tc-breadcrumb, tc-tooltip, tc-context-menu)
- CSS 클래스: `radial-*` -> `tc-*`
- Script: `radial.js` -> `tree_chart.js`

### 3. `app.js`

- `switchToView()`: `display === 'radial'` -> `display === 'tree_chart'`
- Container: `view-radial` -> `view-tree-chart`
- `normalizeViewDef()`: backward compat 추가
  - `display:"radial"` -> `"tree_chart"` 자동 변환
  - `radial_display` -> `tree_chart_options` 자동 이전

### 4. `style.css`

CSS 클래스명 전면 교체:
- `.radial-view-content` -> `.tc-view-content`
- `.radial-toolbar` -> `.tc-toolbar`
- `.radial-canvas-wrap` -> `.tc-canvas-wrap`
- `#radial-canvas` -> `#tc-canvas`
- `#radial-labels` -> `#tc-labels`
- `.radial-breadcrumb` -> `.tc-breadcrumb`
- `.radial-tooltip` -> `.tc-tooltip` (내부: `.rt-*` -> `.tc-tt-*`)
- `.radial-context-menu` -> `.tc-context-menu` (내부: `.rcm-item` -> `.tc-cm-item`)
- `.tc-layout-btn` 스타일 추가

### 5. `validate_manifest.py`

`_validate_hierarchy_view()`에 `tree_chart` display case 추가:
- `tree_chart_options.edge_query` ui_queries 참조 검증
- `tree_chart_options` 내 `detail_view` 참조 검증

### 6. `tests/conftest.py`

Generic fixture 업데이트:
- View key: `category_radial` -> `category_tree_chart`
- `"display": "radial"` -> `"display": "tree_chart"`
- `"radial_display"` -> `"tree_chart_options"` (+ `"default_layout": "radial"` 추가)

### 7. `HANDOFF.md`

아키텍처 문서 반영:
- Generic viewer supports: `tree/nested_table/tree_chart`
- static assets: `tree_chart.js`

## 테스트 결과

```
303 passed in 78.86s
```

전체 테스트 통과 — runtime(218) + MCP(7) + hub_client(24) + CRUD(27) + etc.

## 기술 결정

1. **내부 JS 변수명 유지**: `radialRoot`, `radialCanvas` 등은 그대로 유지하여 diff 최소화
2. **Backward compat**: `normalizeViewDef()`에서 `display:"radial"` 자동 변환 — 기존 .scoda 패키지 호환
3. **Elbow connector**: parent -> vertical -> horizontal -> child 패턴 (클래식 cladogram 스타일)
4. **동적 크기**: leafCount 기반 높이 자동 조절 (MIN_LEAF_SPACING=24px)
5. **Layout toggle**: 두 개 독립 버튼 (active 클래스 토글) — 명시적 모드 표시
