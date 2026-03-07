# P24: Side-by-Side Tree Chart — tree_chart.js 리팩토링 계획

**Date:** 2026-03-07
**Type:** Plan
**Related:** trilobase R02 (tree diff visualization), trilobase devlog 111 (Phase 0+1 완료)
**Mirror:** trilobase devlog/20260307_P03_side_by_side_tree_refactoring.md

## 목표

두 classification profile의 tree chart를 좌우로 나란히 보여주는 Side-by-side 뷰 구현.
이를 위해 tree_chart.js의 전역 상태를 인스턴스화 가능한 구조로 리팩토링한다.

## 현재 문제

`tree_chart.js`는 모듈 전체가 전역 변수에 의존 (1,385줄):

```js
let radialRoot = null;
let radialCanvas = null;
let radialCtx = null;
let radialZoom = null;
let radialQuadtree = null;
// ... 20+ 전역 변수
```

Side-by-side는 두 개의 독립적인 tree를 동시에 렌더링해야 하므로,
같은 로직을 다른 상태로 두 번 실행할 수 있어야 한다.

## 리팩토링 전략: TreeChartInstance 클래스

전역 상태를 클래스 인스턴스 멤버로 이동. 기존 함수들은 인스턴스 메서드로 변환.

### Before (전역 상태)

```
tree_chart.js
  ├── 전역 변수 20+개 (radialRoot, radialCanvas, ...)
  ├── loadRadialView(viewKey)         ← 진입점
  ├── buildRadialHierarchy(view)      ← 데이터 로드
  ├── computeLayout(root, view)       ← 레이아웃 계산
  ├── assignRadialColors(root, view)  ← 색상 부여
  ├── setupRadialZoom()               ← zoom/pan 설정
  ├── renderRadial()                  ← 캔버스 렌더링
  ├── drawLinks(ctx) / drawNodes(ctx) ← 그리기
  ├── updateRadialLabels(t)           ← SVG 라벨
  └── ... (toolbar, search, context menu, breadcrumb)
```

### After (인스턴스 기반)

```
tree_chart.js
  ├── ensureD3Loaded()                ← 유틸 (공유)
  ├── class TreeChartInstance {
  │     constructor(containerId, options)
  │     // 상태 (모두 this.*)
  │     root, fullRoot, prunedRoot, subtreeNode
  │     viewDef, viewKey, transform, quadtree
  │     colorMap, focusNode, depthHidden
  │     searchMatches, canvas, ctx, labelsSvg
  │     zoom, dpr, width, height, outerRadius
  │     layoutMode, cladoBoundsW, cladoBoundsH
  │
  │     // 메서드 (기존 함수 → 인스턴스 메서드)
  │     async load(viewKey, overrideParams?)
  │     async buildHierarchy(view)
  │     computeLayout(root, view)
  │     assignColors(root, view)
  │     setupZoom()
  │     render()
  │     drawLinks(ctx) / drawNodes(ctx, k)
  │     updateLabels(t)
  │     resizeCanvas()
  │     buildToolbar(view)
  │     search(term)
  │     // ... context menu, breadcrumb 등
  │   }
  ├── loadRadialView(viewKey)         ← 기존 진입점 유지 (단일 인스턴스)
  └── loadSideBySideView(viewKey)     ← 새 진입점 (듀얼 인스턴스)
```

## 구현 Phase

### Phase A: TreeChartInstance 클래스 추출 (scoda-engine)

기존 동작을 깨뜨리지 않으면서 전역 상태를 클래스로 이동.

| 단계 | 작업 | 검증 |
|------|------|------|
| A-1 | `TreeChartInstance` 클래스 선언, 전역 변수 → `this.*` 이동 | 기존 단일 tree 동작 확인 |
| A-2 | 기존 함수 → 인스턴스 메서드로 변환 (buildHierarchy, computeLayout, render 등) | 기존 동작 유지 |
| A-3 | `loadRadialView()` → 내부적으로 단일 TreeChartInstance 생성 | 기존 진입점 호환 |
| A-4 | DOM 요소 ID를 하드코딩 → containerId 기반으로 동적 생성 | tc-canvas, tc-labels 등 |
| A-5 | 이벤트 핸들러 (mouse, zoom, resize) → 인스턴스 바인딩 | 각 인스턴스가 자기 canvas에만 반응 |

**핵심 원칙:** 이 단계 완료 후 기존 단일 tree chart가 100% 동일하게 동작해야 함.

### Phase B: Side-by-Side 컨테이너 (scoda-engine + trilobase)

| 단계 | Repo | 작업 |
|------|------|------|
| B-1 | scoda-engine | index.html: side-by-side 컨테이너 추가 (`view-side-by-side`) |
| B-2 | scoda-engine | app.js: `display: "side_by_side"` 뷰 타입 인식 + 라우팅 |
| B-3 | scoda-engine | tree_chart.js: `loadSideBySideView(viewKey)` 구현 |
| B-4 | scoda-engine | style.css: flex 레이아웃 (50:50 분할) |
| B-5 | trilobase | manifest에 side_by_side 뷰 선언 (`compare_view: true`) |

### Phase C: 듀얼 렌더링 (scoda-engine)

| 단계 | 작업 |
|------|------|
| C-1 | `loadSideBySideView()`: 두 TreeChartInstance 생성 (left/right) |
| C-2 | Left: `globalControls.profile_id`로 로드, Right: `globalControls.compare_profile_id`로 로드 |
| C-3 | 각 인스턴스에 profile 이름 라벨 표시 (헤더) |
| C-4 | 두 인스턴스 독립적으로 zoom/pan/collapse/search 동작 확인 |

### Phase D: 동기화 (scoda-engine)

| 단계 | 작업 | 우선순위 |
|------|------|----------|
| D-1 | Zoom/Pan 동기화: 한쪽 zoom → 다른 쪽 mirror | 높음 |
| D-2 | Hover 하이라이트 동기화: 한쪽 hover → 다른 쪽 같은 taxon 하이라이트 | 중간 |
| D-3 | Layout mode 동기화: radial/rectangular 전환 시 양쪽 함께 | 높음 |
| D-4 | Depth toggle 동기화: genus 표시/숨김 양쪽 함께 | 높음 |
| D-5 | Collapse/Expand 동기화: 한쪽 노드 접기 → 다른 쪽 같은 노드 접기 | 낮음 |

## DOM 구조

### 현재 (단일)

```html
<div id="view-tree-chart">
  <div class="tc-view-content">
    <div class="tc-toolbar" id="tc-toolbar"></div>
    <div class="tc-canvas-wrap" id="tc-canvas-wrap">
      <canvas id="tc-canvas"></canvas>
      <svg id="tc-labels"></svg>
    </div>
    <div class="tc-breadcrumb" id="tc-breadcrumb"></div>
    <div class="tc-tooltip" id="tc-tooltip"></div>
    <div class="tc-context-menu" id="tc-context-menu"></div>
  </div>
</div>
```

### Side-by-Side

```html
<div id="view-side-by-side">
  <div class="sbs-toolbar" id="sbs-toolbar">
    <!-- 공유 toolbar: layout toggle, depth toggle, fit, reset -->
  </div>
  <div class="sbs-panels">
    <div class="sbs-panel" id="sbs-left">
      <div class="sbs-panel-header">JA2002 + A2011</div>
      <div class="tc-canvas-wrap" id="sbs-left-wrap">
        <canvas id="sbs-left-canvas"></canvas>
        <svg id="sbs-left-labels"></svg>
      </div>
      <div class="tc-breadcrumb" id="sbs-left-breadcrumb"></div>
    </div>
    <div class="sbs-panel" id="sbs-right">
      <div class="sbs-panel-header">treatise1959</div>
      <div class="tc-canvas-wrap" id="sbs-right-wrap">
        <canvas id="sbs-right-canvas"></canvas>
        <svg id="sbs-right-labels"></svg>
      </div>
      <div class="tc-breadcrumb" id="sbs-right-breadcrumb"></div>
    </div>
  </div>
  <!-- 공유 tooltip, context menu -->
  <div class="tc-tooltip" id="sbs-tooltip"></div>
  <div class="tc-context-menu" id="sbs-context-menu"></div>
</div>
```

## TreeChartInstance 생성자

```js
class TreeChartInstance {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.overrideParams = options.overrideParams || {};  // e.g. {profile_id: 2}
        this.onZoom = options.onZoom || null;                // zoom 동기화 콜백
        this.onHover = options.onHover || null;              // hover 동기화 콜백
        this.showToolbar = options.showToolbar ?? true;
        this.showBreadcrumb = options.showBreadcrumb ?? true;

        // 상태 초기화 (기존 전역 변수들)
        this.root = null;
        this.fullRoot = null;
        this.prunedRoot = null;
        // ... etc
    }
}
```

`overrideParams`가 핵심: `fetchQuery()` 호출 시 `globalControls` 대신 이 값을 사용하면
같은 쿼리를 다른 profile_id로 실행할 수 있다.

## fetchQuery 확장

현재 `fetchQuery()`는 항상 `globalControls`를 병합한다:

```js
async function fetchQuery(queryName, params) {
    const mergedParams = { ...globalControls, ...params };
    // ...
}
```

인스턴스별로 다른 params를 사용하려면:

```js
// TreeChartInstance 내부
async fetchQuery(queryName, params) {
    const mergedParams = { ...globalControls, ...this.overrideParams, ...params };
    // 캐시 키에 overrideParams 포함
}
```

또는 기존 `fetchQuery()`에 params를 명시적으로 전달:

```js
// buildHierarchy 내에서
const rows = await fetchQuery(view.source_query, this.overrideParams);
```

후자가 더 간단하고 기존 캐시 로직과 호환됨. **후자 채택.**

## 리스크 및 대응

| 리스크 | 대응 |
|--------|------|
| 리팩토링 중 기존 동작 깨짐 | Phase A 완료 후 기존 tree chart 동작 검증 필수 |
| 1,385줄 전체 리팩토링 부담 | 기계적 변환 (전역→this) 위주, 로직 변경 최소화 |
| context menu/tooltip 충돌 | 공유 DOM 요소 사용, 표시 시 현재 활성 인스턴스 추적 |
| resize 이벤트 처리 | 각 인스턴스가 자기 container의 resize만 처리 |
| 메모리 (트리 2개) | 5,000노드 × 2 = 10,000 — 문제 없음 |

## 작업 순서

1. **Phase A** (scoda-engine): TreeChartInstance 클래스 추출 — 기존 동작 100% 유지
2. **Phase B** (양쪽): Side-by-side 컨테이너 + 뷰 타입 + manifest
3. **Phase C** (scoda-engine): 듀얼 렌더링 — 두 tree 독립 동작
4. **Phase D** (scoda-engine): 동기화 — zoom/pan, layout mode, depth toggle

예상 작업량: Phase A가 가장 크고 (기계적이지만 양 많음), B~D는 상대적으로 작음.
