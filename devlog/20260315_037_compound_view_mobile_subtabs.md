# Compound View 서브탭 모바일 미표시 수정

**날짜:** 2026-03-15
**커밋:** `cd6a180`

## 문제

Compound view(예: taxonomy diff) 헤더에 profile 드롭다운(`.compound-controls`)과 서브탭(`.compound-sub-tabs`)이 한 행에 배치된다. 모바일 화면에서 `.compound-controls`가 `flex-shrink: 0`으로 인해 가용 폭을 모두 차지해 "diff table", "diff tree" 등 서브탭이 화면 오른쪽으로 밀려나 보이지 않는 문제.

## 원인

```css
.compound-header { display: flex; align-items: center; gap: 16px; }
.compound-controls { flex-shrink: 0; }   /* 줄어들지 않음 */
.compound-sub-tabs { ... }               /* 밀려남 */
```

## 수정

`@media (max-width: 768px)` 블록에 추가:

```css
.compound-header {
    flex-wrap: wrap;
    gap: 6px 16px;
}
.compound-controls {
    width: 100%;          /* 1행: 드롭다운 전체 폭 */
}
.compound-sub-tabs {
    width: 100%;          /* 2행: 서브탭 전체 폭 */
    overflow-x: auto;     /* 항목 많을 때 가로 스크롤 */
    flex-wrap: nowrap;
    padding-bottom: 2px;
}
```

## 결과

모바일에서 compound view 헤더가 2행으로 표시:
- 1행: profile 드롭다운
- 2행: diff table / diff tree 등 서브탭 (가로 스크롤 지원)

CSS 변경만으로 해결, JS 수정 없음.
