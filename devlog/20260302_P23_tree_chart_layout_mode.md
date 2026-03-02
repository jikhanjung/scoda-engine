# P23: Tree Chart — Radial + Rectangular Layout Mode

**Date:** 2026-03-02

## Context

현재 hierarchy view에 radial (방사형) 레이아웃만 지원. Rectangular (직각 분지도) 레이아웃을
추가하여 toolbar 토글로 radial <-> rectangular 전환 가능하게 함. 동시에 용어/파일명을
`radial` -> `tree_chart`로 정리 (radial도 tree chart의 일종이므로).

## Naming / Terminology

| Before | After | 이유 |
|--------|-------|------|
| `radial.js` | `tree_chart.js` | 범용 tree chart 시각화 엔진 |
| `view-radial` (HTML id) | `view-tree-chart` | 컨테이너명 |
| `display: "radial"` | `display: "tree_chart"` | manifest display 값 |
| `radial_display` (manifest) | `tree_chart_options` | 옵션 키 |
| `radial-*` (CSS class) | `tc-*` (tree-chart) | CSS 클래스 간결화 |
| Layout modes | `radial` / `rectangular` | 두 가지 레이아웃 모드 |

내부 JS 변수명(radialRoot 등)은 기존 유지 — 리팩토링 범위 최소화.

## 대상 파일

### 1. `radial.js` -> `tree_chart.js` (rename + 기능 추가)
- State: `treeLayoutMode`, `cladoBoundsW/H`
- `loadRadialView()`: `tree_chart_options.default_layout` 읽기
- `buildRadialToolbar()`: 레이아웃 토글 버튼 추가
- `computeCladogramLayout()`: rectangular 레이아웃 계산
- `computeFitTransform()`: rectangular fit
- `drawGuideCircles()` -> rectangular 가이드선
- `drawLinks()` -> rectangular elbow connector
- `updateRadialLabels()` -> rectangular 수평 라벨

### 2. `index.html` — id/class/script 참조 변경
### 3. `app.js` — display 분기 변경 + backward compat normalizer
### 4. `style.css` — CSS 클래스명 변경
### 5. `validate_manifest.py` — tree_chart 유효성 검사
### 6. `tests/conftest.py` — fixture 업데이트
### 7. `HANDOFF.md` — 아키텍처 문서 반영

## Rectangular Layout 설계

### 좌표 체계
- d3.tree().size([treeH, treeW]) — 수직 spread x 수평 depth
- node.cx = node.y - treeW/2 (depth -> 수평, 원점 중심)
- node.cy = node.x - treeH/2 (spread -> 수직, 원점 중심)
- cladoBoundsW, cladoBoundsH로 전체 범위 저장

### 동적 크기
- leafCount * MIN_LEAF_SPACING (24px) 로 최소 높이 보장
- maxDepth * depthSpacing (120px) 로 너비 결정

### 렌더링 분기
- Guide lines: 수직 dashed 선 (각 depth level)
- Links: elbow connector (parent.cx,parent.cy -> parent.cx,child.cy -> child.cx,child.cy)
- Labels: 모두 수평 (rotation=0), 노드 오른쪽 offset

### Fit Transform
- radial: (canvas size) / (2 * outerRadius + padding)
- rectangular: min(canvas.w / (boundsW + padding), canvas.h / (boundsH + padding))

## Backward Compatibility

`normalizeViewDef()`에서 `display:"radial"` + `radial_display` ->
`display:"tree_chart"` + `tree_chart_options` 자동 변환.
기존 .scoda 패키지가 `radial` display를 사용하더라도 정상 동작.

## Verification
1. `pytest tests/` 전체 통과 (303 tests)
2. 브라우저: 토글 버튼으로 radial <-> rectangular 전환
3. rectangular: elbow 링크, 수평 라벨, zoom/pan, 검색, collapse, 서브트리
