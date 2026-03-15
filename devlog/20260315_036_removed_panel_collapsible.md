# Removed Taxa 패널 접기/펼치기 (모바일 대응)

**날짜:** 2026-03-15

## 문제

Timeline, Diff Tree 등에서 표시되는 Removed Taxa 패널이 모바일 화면에서 넓은 영역을 차지해 tree chart를 가리는 문제.

## 구현

헤더 클릭으로 패널 내용을 접고 펼칠 수 있도록 수정.

### 동작

- 헤더(`Removed (N)`)를 클릭 → 목록 숨김, 헤더만 표시 (접힘)
- 다시 클릭 → 목록 복원 (펼침)
- 접힘/펼침 상태는 `_removedPanelCollapsed` 인스턴스 변수로 유지 → `_updateRemovedPanel()` 재호출 시에도 상태 보존
- 헤더 우측에 `bi-chevron-down` / `bi-chevron-up` 아이콘으로 현재 상태 표시

### 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `scoda_engine/static/js/tree_chart.js` | `_removedPanelCollapsed` 초기화, 헤더 HTML에 chevron 아이콘 추가, 클릭 토글 핸들러 |
| `scoda_engine/static/css/style.css` | `.tc-removed-header` cursor/justify-content 추가, `.tc-removed-panel.collapsed .tc-removed-item { display: none }` |

### 구현 세부

`_updateRemovedPanel()`은 매 morph step / diff 전환 시 재호출되므로 innerHTML을 재설정한 뒤 `.collapsed` 클래스를 인스턴스 변수 기반으로 즉시 복원한다.
