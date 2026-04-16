# 046 — Map Selector View, Supergroup Controls, rank_display Support

Date: 2026-04-16

## Summary

kstrati 패키지를 위해 map_selector 뷰 타입, supergroup 기반 global control, rank_display suffix 지원을 추가했다. paleobase의 meta-package 랜딩 패턴을 일반 패키지에 적용한 첫 사례.

## Changes

### 1. Map Selector View (`app.js`)

- `renderMapSelectorView()`: 배경 이미지 위에 SVG 마커 오버레이
  - manifest의 `supergroup_map` 데이터에서 배경 이미지 경로, viewBox, 마커 위치/색상/라벨 읽기
  - 마커 클릭 → `enterSupergroupView(sgId)` 호출
- `showMapLanding()`: 탭/컨트롤 숨기고 전체화면 지도 표시
  - Home 버튼(navbar-home) 클릭 시 지도 복귀 연결
- `enterSupergroupView()`: supergroup_id + provenance_id 설정 → 탭 빌드 → 뷰 전환
- `switchToView()`에서 `map_selector`는 별도 랜딩이므로 dispatch하지 않음
- `buildViewTabs()`에서 `map_selector` 뷰 제외 (탭에 표시하지 않음)

### 2. Supergroup Global Control

- `renderGlobalControls()`: `source: "supergroup_map"` 지원 (DB 쿼리 없이 manifest에서 옵션 로드)
- supergroup_id 변경 시 provenance_id 자동 동기화 + `updateProvenanceFilter()` 호출
- `loadManifest()`: 초기 로드 시 supergroup/provenance 정합성 검증 (저장된 pref 불일치 교정)
- `manifest.supergroup_map` 감지 시 `showMapLanding()`으로 분기 (탭 모드 건너뜀)

### 3. resolveViewVariant 확장

- `variant_key`로 `supergroup_id` (string) 지원 — 기존 `provenance_id` (integer)에 추가
- `globalControls`에서 variant_key 값을 읽어 해당 variant의 source_query + correlation_display 적용

### 4. rank_display / suffix

- Correlation chart 렌더링: `col.suffix` 속성 지원 → 비어있지 않은 셀 값에 자동 추가
- Tree view: `manifest.rank_display[rank].abbr`를 노드 라벨에 자동 추가

### 5. HTML/CSS

- `index.html`: `#view-map` 컨테이너 추가
- `style.css`: `.map-selector-*` 스타일 (frame, bg, overlay, marker)
- `static/images/`: kstrati 패키지용 배경 이미지 배치 (임시, 향후 .scoda assets 서빙으로 전환)

## Files Modified

| File | Changes |
|------|---------|
| `scoda_engine/static/js/app.js` | renderMapSelectorView, showMapLanding, enterSupergroupView, updateProvenanceFilter, renderGlobalControls 확장, resolveViewVariant, buildViewTabs, switchToView, tree label rank_display, correlation suffix |
| `scoda_engine/templates/index.html` | #view-map 컨테이너 |
| `scoda_engine/static/css/style.css` | map-selector-* 스타일, map-marker 스타일, rank suffix 관련 |
| `scoda_engine/static/images/` | KoreanPeninsulaGeolMap.png (kstrati용) |

## Design Notes

- map_selector는 scoda-engine의 범용 기능이 아닌 kstrati 특화 패턴. 다른 패키지가 지도 기반 선택기를 쓸 수 있지만 현재는 kstrati만 사용.
- 배경 이미지는 현재 scoda-engine static에 배치. 향후 .scoda 패키지 assets 서빙 API를 추가하면 패키지 내부에서 로드하도록 전환해야 함.
- rank_display는 manifest 수준 기능으로, 어떤 패키지든 `rank_display` 매핑을 선언하면 tree view에서 자동 적용됨.
