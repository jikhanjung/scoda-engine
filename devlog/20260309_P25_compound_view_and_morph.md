# P25: Compound View + Animated Morphing

**Date:** 2026-03-09
**Status:** Plan
**Relates to:** trilobase `devlog/20260309_P82_animated_morphing_plan.md`

## 목표

1. **Compound View 타입** 도입 — 하나의 탭 안에 로컬 컨트롤 + 서브탭을 가진 복합 뷰
2. **Animated Morphing** — 두 프로필 트리 사이의 위치 보간 애니메이션 (새 display 타입)

## 배경

현재 Compare 기능이 3개의 최상위 탭(Diff Table, Diff Tree, Side-by-Side)으로 분산되어 있고, 글로벌 `compareMode` 토글로 관리됨. 이를 하나의 "Profile Comparison" 탭으로 통합하여 UX를 개선하고, Animated Morphing을 서브뷰로 추가한다.

## Manifest 스펙: `type: "compound"`

```json
{
  "profile_comparison": {
    "type": "compound",
    "title": "Profile Comparison",
    "icon": "bi-arrow-left-right",
    "controls": [
      { "type": "select", "param": "base_profile_id", "label": "From", ... },
      { "type": "select", "param": "compare_profile_id", "label": "To", ... }
    ],
    "sub_views": {
      "diff_table": { "title": "Table", ... },
      "diff_tree": { "title": "Tree", ... },
      "morph": { "title": "Morph", "display": "tree_chart_morph", ... }
    },
    "default_sub_view": "diff_table"
  }
}
```

- `controls`: 탭 로컬 컨트롤 (글로벌이 아님). 서브뷰 쿼리의 `$param` 참조에 주입.
- `sub_views`: 서브탭으로 렌더링되는 뷰 정의들. 각 서브뷰는 기존 뷰 스펙과 동일한 형식.
- `default_sub_view`: 초기 활성 서브탭.

## scoda-engine 변경사항

### 1. app.js

#### 1-1. `loadCompoundView(viewKey, view)`
- compound 컨테이너 표시
- `view.controls` → 로컬 셀렉터 렌더링 (`#compound-controls`)
- `view.sub_views` → 서브탭 버튼 렌더링 (`#compound-sub-tabs`)
- 서브탭 클릭 → `switchCompoundSubView(subKey)`
- 로컬 컨트롤 변경 → 현재 서브뷰 리프레시

#### 1-2. `switchCompoundSubView(subKey)`
- 서브뷰 정의에 따라 적절한 렌더러 호출
- `display: "table"` → renderTableView (compound 컨텐츠 영역에)
- `display: "tree_chart"` → loadRadialView (compound 컨텐츠 영역에)
- `display: "side_by_side"` → loadSideBySideView (compound 컨텐츠 영역에)
- `display: "tree_chart_morph"` → loadMorphView (새 렌더러)

#### 1-3. compareMode 제거
- 글로벌 `compareMode` 변수 삭제
- `renderGlobalControls()`에서 `compare_control` 관련 show/hide 제거
- `switchToView()`에서 `compare_view` 자동 토글 제거
- 매니페스트에서 `compare_control: true`, `compare_view: true` 플래그 무시 (하위호환)

### 2. index.html

```html
<div class="view-container" id="view-compound" style="display: none;">
    <div class="compound-controls" id="compound-controls"></div>
    <ul class="nav nav-tabs nav-tabs-sm" id="compound-sub-tabs"></ul>
    <div class="compound-sub-content" id="compound-sub-content">
        <!-- 서브뷰별 컨테이너: JS에서 동적 생성 -->
    </div>
</div>
```

### 3. tree_chart.js — Animated Morphing

#### 3-1. `loadMorphView(viewKey, subView, compoundParams)`
- Base 프로필 트리 빌드 → `basePositions` 스냅샷
- Compare 프로필 트리 빌드 → `comparePositions` 스냅샷
- 초기 상태: base 프로필 트리 표시
- Morph 컨트롤 (Play/Pause, Scrubber, Speed) 표시

#### 3-2. `snapshotPositions(root)` → `Map<nodeId, {cx, cy, color, radius}>`
- `root.each()` 순회, collapsed `_children` 포함
- Collapsed 자식은 부모 위치를 fallback

#### 3-3. `animateMorph(fromPos, toPos, duration)`
- `requestAnimationFrame` 루프
- Easing: cubic ease-in-out
- 노드: `lerp(from, to, t)` 위치/색상/크기
- Added: fade-in + grow (부모 위치에서)
- Removed: fade-out + shrink
- Edge crossfade: old-only opacity↓, new-only opacity↑, shared 보간

#### 3-4. Morph UI 컨트롤
- Play/Pause 버튼
- Scrubber 슬라이더 (0~100%)
- Speed 셀렉터 (0.5x / 1x / 2x)
- Direction 토글 (From→To / To→From)

### 4. style.css
- `.compound-controls`: From/To 셀렉터 인라인 레이아웃
- `.compound-sub-tabs`: 서브탭 스타일 (기존 nav-tabs 활용)
- `.morph-controls`: Play/Scrubber 컨트롤바

## 구현 순서

| Step | 내용 |
|------|------|
| 1 | index.html: compound 컨테이너 추가 |
| 2 | app.js: `loadCompoundView()` + 로컬 컨트롤 + 서브탭 |
| 3 | app.js: 기존 table/tree_chart 렌더러를 compound 서브뷰에서 호출 가능하게 |
| 4 | app.js: compareMode 글로벌 상태 제거 |
| 5 | style.css: compound 뷰 스타일 |
| 6 | tree_chart.js: `snapshotPositions()` |
| 7 | tree_chart.js: `loadMorphView()` + `animateMorph()` |
| 8 | tree_chart.js: Morph UI 컨트롤 |
| 9 | tree_chart.js: Edge crossfade |
| 10 | 테스트: default ↔ treatise1959 ↔ treatise2004 |

## 참고

- trilobase P82: `devlog/20260309_P82_animated_morphing_plan.md`
- R02: `(trilobase) devlog/20260302_R02_tree_diff_visualization.md`
- Side-by-Side: `devlog/20260307_P24_side_by_side_tree_refactoring.md`
