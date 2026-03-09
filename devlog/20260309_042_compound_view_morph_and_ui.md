# 042: Compound View, Morphing Animation, Rendering Overhaul

**Date:** 2026-03-09
**Relates to:** P25, trilobase `devlog/20260309_115_compound_view_and_morphing.md`

## 요약

Compound View 타입 구현, Morphing 애니메이션 추가, tree_chart 렌더링 대폭 단순화, 다수의 UX 개선.

## 변경 파일

### `scoda_engine/static/js/tree_chart.js`

**Morphing 기능:**
- `loadMorph()` — base/compare 두 트리 빌드 + layout + 스냅샷
- `renderMorphFrame(t)` — 두 스냅샷 간 위치/색상/투명도 보간 렌더링
- `startMorphAnimation(speed, reversed, onProgress, onDone)` — 정방향/역방향 재생
- `stopMorphAnimation()` — 애니메이션 정지
- `snapshotPositions()` — cx, cy, x(angle), y(radius), color, r 저장
- `snapshotLinks()` — parent-child 연결 스냅샷
- `_drawMorphLabels()` — morph 중 canvas label with fade in/out
- `_navigateMorphSubtree()`, `_rebuildMorphFromFullTree()` — morph 중 view-as-root

**렌더링 단순화:**
- SVG label overlay 제거 → `drawLabels(ctx)` canvas 기반
- zoom 의존적 노드/폰트 크기 조절 제거 → 비트맵 스케일링
- depth toggle, bitmap cache, 동적 radius 조절 모두 제거
- 노드 radius=8, font=20px 고정 (textScale 적용)

**Text Scale:**
- `radiusScale` → `textScale` 전환
- A−/A+ 버튼으로 font/node 크기 직접 조절
- layout 재계산 불필요, `render()`만 호출
- `onTextScaleSync` 콜백으로 Side-by-Side 동기화

**Radial tree link 통일:**
- morph에서도 `quadraticCurveTo` 곡선 사용 (이전: 직선)
- rectangular에서도 morph 시 L자형 직각 연결

**Rectangular tree depth spacing 수정:**
- rank alignment을 `treeW` 비례 → present rank 수 × depthSpacing 기반으로 변경
- view-as-root 시 depth spacing 일관성 보장
- morph에서 두 트리 cladoBounds를 max로 통합

**기타:**
- `computeFitTransform()` radial 모드에 10% margin 추가
- LEAF_GAP 6→12, SUBTREE_GAP 8→16
- scaleExtent [0.001, 100]
- morph duration 3200ms / speed

### `scoda_engine/static/js/app.js`

- `loadCompoundView()` — compound view 렌더링 (로컬 컨트롤 + sub-tabs)
- `switchCompoundSubView()` — sub-view 전환
- `renderCompoundMorphSubView()` — morph UI (transport controls + scrubber + speed)
- `fetchCompoundQuery()` — compound 컨트롤 merge
- `_showLoading()` / `_hideLoading()` — global loading indicator (progress bar + wait cursor)
- `buildViewTabs()` — Show Text / Hide Text 토글 버튼 추가
- `loadTree()` — genera_count 동적 계산 (taxonomy_tree_genera_counts fetch + propagate)

### `scoda_engine/static/css/style.css`

- `.compound-*` — compound view header, controls, sub-tabs 스타일
- `.morph-controls` — transport buttons (rewind, backward, pause, forward, ff)
- `.global-loading-bar` — animated gradient progress bar
- `body.loading-active` — wait cursor
- `.view-tab-toggle` — Show Text 버튼
- `.tc-text-smaller`, `.tc-text-larger` — text scale 버튼
- `.view-tabs.show-all-text` — 모든 탭 label 표시

### `scoda_engine/templates/index.html`

- `view-compound` 컨테이너 div 추가
- `global-loading-bar` div 추가 (navbar 아래)

### `core/scoda_engine_core/validate_manifest.py`

- `'compound'`를 `KNOWN_VIEW_TYPES`에 추가
- `_validate_compound_view()` 함수 추가

## 성능 개선

- taxonomy_tree genera_count: 10,310ms → 9ms (per-row recursive CTE → 별도 단순 쿼리 + JS 전파)
- text scale 변경: layout 재계산 → render()만 호출 (즉각 반응)

## 호환성

- 기존 manifest의 `tree_chart`, `side_by_side`, `table` display 타입은 그대로 작동
- 새로운 `compound` view 타입과 `tree_chart_morph` display 타입 추가
- `compare_view` 방식의 기존 뷰도 호환 (하위 호환)
