# 039: Side-by-Side Tree Chart — TreeChartInstance 리팩토링 + 듀얼 렌더링

**날짜:** 2026-03-07
**Related:** P24 (devlog/20260307_P24_side_by_side_tree_refactoring.md), trilobase devlog 112

## 개요

`tree_chart.js`의 전역 상태를 `TreeChartInstance` 클래스로 리팩토링하여,
두 개의 독립적인 tree chart를 동시에 렌더링할 수 있게 했다.
이를 기반으로 Side-by-Side 뷰를 구현하여 두 classification profile의 tree를 나란히 비교할 수 있다.

## 변경 내용

### 1. TreeChartInstance 클래스 (tree_chart.js)

**전역 → 인스턴스 전환:**
- 전역 변수 20+개 (`radialRoot`, `radialCanvas`, `radialZoom` 등) → `this.*` 인스턴스 멤버
- 전역 함수 30+개 → 클래스 메서드
- 파일 크기: 1,385줄 → 1,376줄 (구조만 변경, 로직 동일)

**생성자 옵션:**
```js
new TreeChartInstance({
    wrapEl,           // canvas wrap 요소 (필수)
    toolbarEl,        // toolbar 요소 (null이면 생략)
    breadcrumbEl,     // breadcrumb 요소
    tooltipEl,        // tooltip 요소 (공유 가능)
    contextMenuEl,    // context menu 요소 (공유 가능)
    overrideParams,   // fetchQuery 시 globalControls override
})
```

**인스턴스 관리:**
- `_allInstances[]`: 모든 활성 인스턴스 추적 (resize, click 처리)
- `_singletonTC`: 기존 단일 뷰 backward compat
- `_sbsLeft`, `_sbsRight`: side-by-side 인스턴스
- `destroy()`: 인스턴스 정리 (이벤트 리스너 해제, 배열에서 제거)

**DOM 동적 생성:**
- `load()` 시 `wrapEl.innerHTML = '<canvas></canvas><svg></svg>'` — ID 불필요
- HTML에서 초기 canvas/svg 요소 제거
- CSS: `#tc-canvas`, `#tc-labels` → `.tc-canvas-wrap canvas`, `.tc-canvas-wrap svg`

**context menu/breadcrumb:**
- inline `onclick="rcmViewAsRoot()"` → `addEventListener` + 클로저로 인스턴스 바인딩
- 전역 stub 함수 (`rcmViewAsRoot` 등) 제거

### 2. Side-by-Side 뷰

**HTML (index.html):**
- `view-side-by-side` 컨테이너: sbs-panels (flex), 좌/우 패널, 공유 toolbar/tooltip/context-menu

**CSS (style.css):**
- `.sbs-panels`: `display: flex; flex: 1`
- `.sbs-panel`: `flex: 1; border-right` (구분선)
- `.sbs-panel-header`: 프로필 이름 오버레이

**JS (tree_chart.js) — `loadSideBySideView(viewKey)`:**
- Left 인스턴스: `globalControls.profile_id` 사용
- Right 인스턴스: `overrideParams: { profile_id: compare_profile_id }` 로 다른 프로필 로드
- `Promise.all`로 병렬 로드
- 프로필 이름 헤더 표시 (`classification_profiles_selector` 쿼리)

**`_setupSbsSync(left, right)`:**
- Zoom/pan 동기화: `syncing` flag로 무한 루프 방지
- Layout mode 동기화: `switchLayout()` override

### 3. app.js 변경

- `display: "side_by_side"` 뷰 타입 → `view-side-by-side` 컨테이너 표시 + `loadSideBySideView()` 호출
- Compare 버튼 제거: `compare_view` 탭 전환 시 자동 `compareMode` 활성화
- `updateCompareViewTabs()` 함수 제거 (불필요)

### 4. v0.2.0 버전 범프

TreeChartInstance 리팩토링이 API 호환성에 영향 없지만,
내부 구조 변경이 크므로 마이너 버전을 올림.

## 검증

- 기존 단일 Tree Chart 뷰: radial/rectangular 레이아웃, zoom, search, collapse, context menu, breadcrumb 모두 정상 동작
- Side-by-Side 뷰: 좌우 패널 독립 렌더링, zoom/pan 동기화, layout 전환 동기화 확인
- Profile Diff 탭: compare 셀렉터 자동 표시/숨김 정상

## 수정 파일

| 파일 | 변경 |
|------|------|
| `static/js/tree_chart.js` | 전역→TreeChartInstance 클래스, loadSideBySideView, zoom sync |
| `static/js/app.js` | side_by_side 라우팅, Compare 버튼 제거, auto compareMode |
| `static/css/style.css` | sbs-* 스타일, #tc-canvas/#tc-labels → class 셀렉터 |
| `templates/index.html` | view-side-by-side 컨테이너, canvas/svg 초기 요소 제거 |
| `pyproject.toml` | v0.1.9 → v0.2.0 |
| `scoda_engine/__init__.py` | v0.1.9 → v0.2.0 |
