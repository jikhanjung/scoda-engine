# P20: Radial Hierarchy Display Mode

**날짜**: 2026-02-28
**상태**: 계획
**관련**: trilobase P75 (radial taxonomy tree visualization)

## 목적

기존 hierarchy 뷰의 새 display mode로 `"radial"`을 추가한다. hierarchy 데이터를 방사형(radial) 트리로 렌더링하여 루트를 중앙에, leaf를 최외곽에 배치하고 zoom in/out으로 탐색 가능하게 한다.

모든 SCODA 패키지에서 hierarchy 데이터가 있으면 사용 가능한 범용 기능.

## 현재 뷰 시스템

```
type: "hierarchy"
  ├── display: "tree"          → view-tree (DOM 트리 + 리스트 패널)
  ├── display: "nested_table"  → view-chart (계층 테이블)
  └── display: "radial"        → view-radial (신규: Canvas+SVG 방사형)

type: "table"                  → view-table
type: "detail"                 → (모달)
```

## 기술 스택

| 항목 | 선택 | 이유 |
|------|------|------|
| 레이아웃 | D3.js v7 `d3.cluster()` + radial projection | 표준 radial tree 알고리즘 |
| 렌더링 | **Canvas**(노드/링크) + **SVG overlay**(라벨) | 5,000+ 노드 성능 확보 |
| 줌 | `d3.zoom()` + semantic LOD | 줌 레벨별 표시 정보 변화 |
| D3 로딩 | CDN lazy load (radial 뷰 진입 시에만) | 다른 뷰에 영향 없음 |

---

## 구현 단계

### Step 1: HTML 컨테이너 추가

**파일**: `scoda_engine/templates/index.html`

기존 `view-chart` 아래에 추가:

```html
<!-- View: Radial (hierarchy radial tree) -->
<div class="view-container" id="view-radial" style="display: none;">
    <div class="radial-view-content">
        <div class="radial-toolbar" id="radial-toolbar"></div>
        <div class="radial-canvas-wrap" id="radial-canvas-wrap">
            <canvas id="radial-canvas"></canvas>
            <svg id="radial-labels"></svg>
        </div>
        <div class="radial-breadcrumb" id="radial-breadcrumb"></div>
        <div class="radial-tooltip" id="radial-tooltip" style="display:none;"></div>
    </div>
</div>
```

### Step 2: switchToView() 분기 추가

**파일**: `scoda_engine/static/js/app.js`

`switchToView()` 함수에서:

```javascript
const radialContainer = document.getElementById('view-radial');
// ... 기존 컨테이너들과 함께 hide
radialContainer.style.display = 'none';

if (view.type === 'hierarchy') {
    if (view.display === 'tree') {
        // 기존 로직
    } else if (view.display === 'nested_table') {
        // 기존 로직
    } else if (view.display === 'radial') {
        radialContainer.style.display = '';
        loadRadialView(viewKey);
    }
}
```

`loadRadialView()`는 D3를 lazy load한 뒤 `radial.js`의 초기화 함수 호출.

### Step 3: Radial 렌더링 모듈

**파일**: `scoda_engine/static/js/radial.js` (신규)

핵심 구조:

```
loadRadialView(viewKey)
  ├── ensureD3Loaded()              // D3 CDN lazy load
  ├── fetchNodes(sourceQuery)       // hierarchy_options의 source_query
  ├── fetchEdges(edgeQuery, params) // radial_display.edge_query (선택)
  ├── buildHierarchy(nodes, edges)  // d3.stratify() → d3.hierarchy
  ├── computeLayout(root)           // d3.cluster() + rank-pinned radii
  └── render(root)
       ├── drawCanvas(root)         // 동심원, 링크, 노드
       ├── updateLabels(root, transform)  // SVG 라벨 (LOD)
       └── setupInteractions()      // zoom, hover, click, search
```

#### 3a. D3 Lazy Loading

```javascript
let d3Ready = null;
function ensureD3Loaded() {
    if (d3Ready) return d3Ready;
    d3Ready = new Promise((resolve, reject) => {
        if (window.d3) return resolve();
        const script = document.createElement('script');
        script.src = 'https://d3js.org/d3.v7.min.js';
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
    return d3Ready;
}
```

#### 3b. 데이터 → Hierarchy 구축

두 가지 모드 지원:

- **기본**: `source_query`에 parent_key가 포함된 flat rows → `d3.stratify()` 직접 사용
- **분리 엣지**: `radial_display.edge_query` 지정 시 → 노드와 엣지를 별도 로드, 엣지로 parent 매핑 후 stratify

```javascript
async function buildHierarchy(viewDef) {
    const hOpts = viewDef.hierarchy_options;
    const rOpts = viewDef.radial_display || {};
    const nodes = await fetchQuery(viewDef.source_query);

    if (rOpts.edge_query) {
        const edges = await fetchQuery(rOpts.edge_query, rOpts.edge_params);
        const parentMap = new Map(edges.map(e => [e.child_id, e.parent_id]));
        nodes.forEach(n => { n[hOpts.parent_key] = parentMap.get(n[hOpts.id_key]) || null; });
    }

    return d3.stratify()
        .id(d => d[hOpts.id_key])
        .parentId(d => d[hOpts.parent_key])
        (nodes);
}
```

#### 3c. Radial Cluster Layout

```javascript
function computeLayout(root, outerRadius, rankRadius) {
    d3.cluster().size([360, outerRadius])(root);

    // rank별 고정 반지름 오버라이드
    if (rankRadius) {
        root.each(node => {
            const rank = node.data[rankKey];
            if (rankRadius[rank] !== undefined) {
                node.y = rankRadius[rank] * outerRadius;
            }
        });
    }
}
```

#### 3d. Canvas 렌더링

- **동심원 가이드**: rank별 얇은 회색 원
- **링크**: `d3.linkRadial()` 커브 (부모→자식)
- **노드**: rank별 크기 다른 원 (상위 rank 클수록 큼)
- **색상**: 최상위 자식 노드(Order 등) 기준 고유 색, 하위 상속
- **내부 노드 아크**: count_key에 비례하는 두께의 호

#### 3e. Semantic LOD (Level of Detail)

| 줌 레벨 (k) | 표시 내용 |
|-------------|-----------|
| k < 1.5 | 최상위 rank 이름만. 최하위 영역은 색 띠 |
| 1.5 ≤ k < 3 | + 중간 rank 이름 |
| 3 ≤ k < 6 | + 하위 rank 이름. leaf는 점만 |
| k ≥ 6 | + 뷰포트 내 leaf 이름 (viewport culling) |

viewport culling으로 동시 라벨 ~150개 이하 유지.

#### 3f. 인터랙션

- **Zoom/Pan**: `d3.zoom()` scaleExtent [0.3, 30]
- **Hover**: `d3.quadtree()`로 최근접 노드 → 툴팁 (이름, rank, author 등)
- **Click**: 내부 노드 → animated zoom to subtree
- **Double-click**: 한 단계 위로 zoom out
- **Breadcrumb**: 현재 focus 경로, 클릭으로 이동
- **Depth 토글**: `radial_display.depth_toggle: true`이면 leaf_rank 포함/제외 토글 표시
- **검색**: 툴바에 검색 입력 → 매칭 노드 하이라이트 + zoom to
- **Detail 연동**: `radial_display.on_node_click` 설정 시 클릭으로 detail 모달 열기

### Step 4: CSS 추가

**파일**: `scoda_engine/static/css/style.css`

```css
/* Radial view */
.radial-view-content { position: relative; height: calc(100vh - 98px); overflow: hidden; }
.radial-toolbar { position: absolute; top: 8px; right: 16px; z-index: 10; display: flex; gap: 8px; }
.radial-canvas-wrap { width: 100%; height: 100%; position: relative; }
#radial-canvas { width: 100%; height: 100%; }
#radial-labels { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }
.radial-breadcrumb { position: absolute; top: 8px; left: 16px; z-index: 10; }
.radial-tooltip { position: absolute; z-index: 20; background: #fff; border: 1px solid #dee2e6;
                   border-radius: 4px; padding: 8px 12px; font-size: 0.85rem; pointer-events: none;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.15); max-width: 300px; }
```

### Step 5: Manifest 스키마 문서화

`radial_display` 옵션 스키마:

```json
{
  "edge_query": "string (선택) — 별도 엣지 쿼리. 없으면 source_query의 parent_key 사용",
  "edge_params": "object (선택) — edge_query에 전달할 파라미터",
  "color_key": "string (선택) — 색상 그룹 기준 필드",
  "count_key": "string (선택) — 노드 크기/아크 두께 기준 필드",
  "depth_toggle": "boolean (선택) — leaf rank 포함/제외 토글 표시",
  "leaf_rank": "string (선택) — leaf rank 이름 (depth_toggle용)",
  "rank_radius": "object (선택) — rank별 반지름 비율 {rank: 0.0~1.0}",
  "on_node_click": "object (선택) — 클릭 시 detail view 연동"
}
```

---

## 수정 파일 목록

| 파일 | 작업 |
|------|------|
| `scoda_engine/templates/index.html` | `view-radial` 컨테이너 추가 |
| `scoda_engine/static/js/app.js` | `switchToView()` radial 분기 + `loadRadialView()` |
| `scoda_engine/static/js/radial.js` | **신규** — D3 lazy load + radial 렌더링 전체 |
| `scoda_engine/static/css/style.css` | radial 뷰 스타일 추가 |

---

## 검증 방법

1. hierarchy 데이터가 있는 SCODA 패키지에 `display: "radial"` 뷰 추가
2. 엔진 기동 → Radial Tree 탭 표시 확인
3. D3.js lazy load → Canvas에 방사형 트리 렌더링
4. 줌 인/아웃 → LOD 변화 (상위 rank → 하위 rank 순차 표시)
5. depth_toggle → leaf 포함/제외 전환
6. 노드 hover → 툴팁 / click → detail 모달
7. 검색 → 노드 하이라이트 + 자동 줌
8. 기존 tree/nested_table/table 뷰에 영향 없음 확인

---

## 설계 원칙

- **범용성**: trilobase 고유 로직 없음. hierarchy_options + radial_display만으로 동작
- **Lazy load**: D3.js는 radial 뷰 진입 시에만 로드. 다른 뷰 성능 영향 제로
- **기존 패턴 준수**: fetchQuery(), switchToView(), detail 모달 등 기존 app.js 패턴 재사용
- **점진적 확장**: edge_query, depth_toggle, rank_radius 등은 모두 선택 옵션
