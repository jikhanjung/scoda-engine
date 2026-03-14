# Timeline 축 전환 시 빈 트리 처리 버그 수정

**Date**: 2026-03-14

## 문제

Timeline에서 축 모드(geologic ↔ pubyear)를 전환할 때, `buildHierarchy()`가 빈 결과를 반환하면 이전 트리가 캔버스에 그대로 남는 버그.

**원인**: `buildHierarchy()`가 빈 rows를 받으면 `null`을 반환하지만 `fullRoot`을 클리어하지 않아서, `loadStep()`에서 `inst.root = inst.fullRoot`이 이전 트리를 참조.

## 수정

### `tree_chart.js`
- `buildHierarchy()`: 빈 결과 시 `this.fullRoot = null` 설정 후 return

### `app.js`
- `loadStep()`: `inst.root`이 null이면 빈 캔버스 렌더링 (`inst.render()`) 후 return
- `loadAxis()`, `loadStep()`, 드롭다운 change 핸들러에 `[timeline]` 디버그 로그 추가

## 수정 파일

- `scoda_engine/static/js/app.js`
- `scoda_engine/static/js/tree_chart.js`
