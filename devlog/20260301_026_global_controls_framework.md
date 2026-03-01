# 027: Global Controls 프레임워크 구현

**날짜**: 2026-03-01
**커밋**: bb63a57

## 배경

trilobase P79에서 profile 기반 taxonomy 쿼리를 구현하면서, scoda-engine 측에 manifest-driven global controls 프레임워크가 필요해짐. manifest의 `global_controls` 배열을 파싱하여 UI 상단에 드롭다운 셀렉터를 렌더링하고, 선택값을 모든 쿼리에 자동으로 병합하는 구조.

## 변경 사항

### `scoda_engine/static/js/app.js`
- `globalControls` 상태 변수 추가
- `loadManifest()`: `manifest.global_controls` 파싱 → 기본값 설정 → `renderGlobalControls()` 호출
- `renderGlobalControls()`: `source_query`에서 옵션 로드, 드롭다운 렌더링, change 이벤트 시 캐시 무효화 + 뷰 갱신
- `fetchQuery()`: `globalControls` 값을 모든 쿼리 params에 자동 병합
- `selectTreeLeaf()`: leaf item 쿼리에도 globalControls 병합
- tree `isLeaf` 판정 로직 수정 — children 없는 노드도 leaf로 처리

### `scoda_engine/static/js/radial.js`
- radial tree `edge_params`에서 `$variable` 참조를 globalControls 값으로 치환

### `scoda_engine/static/css/style.css`
- `.global-control-item`, `.global-control-label`, `.global-control-select` 스타일 추가

### `scoda_engine/templates/index.html`
- `#global-controls` 컨테이너 div 추가

## 참고

- 이 커밋에서는 선택값을 `localStorage`에 저장했으나, 이후 026에서 overlay DB 저장으로 교체됨
