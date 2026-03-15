# P30: 모바일 UI 개선 — Landing 스크롤 + Tree 드로어

**날짜:** 2026-03-15
**상태:** 구현 완료

---

## 1. 배경

P27에서 768px breakpoint 기반 모바일 반응형 UI를 도입했으나 두 가지 문제가 남아 있었다.

1. **Landing 페이지 스크롤 불가**: 패키지가 화면보다 많을 때 모바일에서 스크롤 불가, 첫 2~3개만 보임
2. **Tree 뷰 right panel 안 보임**: taxonomy tree에서 왼쪽 트리 패널이 뷰 전체를 차지해 오른쪽 genus 목록이 보이지 않음

---

## 2. 원인 분석

### 2-1. Landing 스크롤 불가

`landing.html`의 body에 `overflow: hidden`이 적용되어 있음.
D3 force canvas(`position: fixed`)의 배경 처리를 위해 추가됐으나, 콘텐츠 스크롤까지 차단.

### 2-2. Tree 뷰 오른쪽 패널 숨김

`index.html`의 tree 뷰가 Bootstrap 그리드 사용:
```html
<div class="col-md-4 tree-panel">   <!-- 768px 미만 → 100% 폭 -->
<div class="col-md-8 list-panel">   <!-- 아래로 밀려남 -->
```

모바일에서 `.row.h-100` + `flex-wrap: wrap` 조합으로 tree-panel이 뷰 전체 높이를 차지,
list-panel이 화면 아래로 밀려나고 `body { overflow: hidden }`으로 스크롤도 불가.

---

## 3. 설계 결정

### 3-1. Landing: `overflow-y: auto`로 변경

`#canvas`가 `position: fixed`라 body overflow 변경이 배경 애니메이션에 영향 없음.

### 3-2. Tree 뷰: 슬라이드 드로어(Drawer) 패턴

단순 수직 분할(40/60) 대신 **드로어 패턴** 채택:
- 기본: list-panel 전체 폭, tree-panel 숨김
- list-panel 헤더의 토글 버튼(🌳) 클릭 → tree-panel이 왼쪽에서 슬라이드인 (overlay)
- backdrop 탭 또는 트리 항목 선택 시 자동으로 닫힘

**선택 이유:**
- 트리는 탐색용 패널 → 항목 선택 후 닫히는 게 자연스러운 UX
- list-panel이 항상 full-width로 표시되어 가독성 우수
- 데스크톱 레이아웃 변경 없음

---

## 4. 구현

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `scoda_engine/templates/landing.html` | `body { overflow: hidden }` → `overflow-y: auto` |
| `scoda_engine/static/css/style.css` | 모바일 드로어 CSS (tree-panel overlay, backdrop, slide animation) |
| `scoda_engine/templates/index.html` | list-panel 헤더 토글 버튼, backdrop div 추가 |
| `scoda_engine/static/js/app.js` | `toggleMobileTree()` 함수, 트리 선택 시 자동 닫힘 |

### CSS 핵심 로직

```css
@media (max-width: 768px) {
    /* list-panel: 전체 폭 */
    #view-tree .list-panel { flex: 0 0 100%; max-width: 100%; }

    /* tree-panel: 왼쪽 overlay drawer */
    #view-tree .tree-panel {
        position: absolute; top: 0; left: 0;
        width: 80%; max-width: 300px; height: 100%;
        z-index: 100;
        transform: translateX(-100%);
        transition: transform 0.25s ease;
    }
    #view-tree .tree-panel.mobile-open {
        transform: translateX(0);
    }
}
```

### JS 핵심 로직

```js
function toggleMobileTree() {
    const panel = document.querySelector('.tree-panel');
    const backdrop = document.getElementById('tree-backdrop');
    panel.classList.toggle('mobile-open');
    backdrop.classList.toggle('visible');
}
```

트리 항목 선택(`selectNode`) 시 모바일에서 자동으로 드로어 닫힘.

---

## 5. 구현 세부사항

### list-header 재렌더링 문제

`selectTreeLeaf()` 호출 시 `list-header` innerHTML을 덮어쓰기 때문에, 초기 HTML에 넣은 토글 버튼이 사라지는 문제가 있었다. JS에서 헤더를 렌더링하는 코드(`header.innerHTML = ...`)에도 동일한 토글 버튼 마크업을 추가해 해결.

### backdrop 위치 기준점

`#tree-backdrop`은 `#view-tree` 직하위에 있고 `position: absolute; inset: 0`으로 뷰 전체를 덮어야 한다. 이를 위해 `.view-container`에 `position: relative`를 추가했다. 다른 뷰 컨테이너에도 적용되나 레이아웃에는 영향 없음.

### `selectTreeLeaf` 자동 닫힘

트리에서 leaf 노드를 선택하면 `closeMobileTree()`가 먼저 호출되어 드로어가 닫히고 오른쪽 패널의 목록이 바로 보인다. 데스크톱에서는 `tree-panel` / `tree-backdrop` 요소가 `.mobile-open` 클래스를 갖지 않아 `classList.remove` 호출이 no-op으로 무해하다.

## 6. 데스크톱 영향

없음. CSS 드로어 로직은 `@media (max-width: 768px)` 블록 내에 격리. `position: relative` 추가는 기존 레이아웃에 영향 없음.

## 7. 테스트

`pytest tests/` — 303/303 통과.
