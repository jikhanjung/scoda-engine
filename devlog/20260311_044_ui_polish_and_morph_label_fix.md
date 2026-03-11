# 044: UI 개선 — Show Text 아이콘화 + Morph 라벨 보간 + Diff legend 위치

**Date:** 2026-03-11
**Version:** 0.2.3

## 변경 사항

### 1. Show Text / Hide Text → 눈 아이콘 + T (app.js)

탭 바의 텍스트 토글 버튼을 아이콘 기반으로 변경:
- 접힌 상태: `bi-eye-slash` + T
- 펼친 상태: `bi-eye` + T

### 2. Morph 라벨 각도 보간 (tree_chart.js)

**문제**: Animation 뷰에서 노드가 이동할 때 라벨 각도가 t=0.5 지점에서
갑자기 바뀜. `node.x` (angle)가 보간되지 않고 activeRoot 전환 시 점프했기 때문.

**수정**:
- `renderMorphFrame()`: `node.x`, `node.y`도 eased interpolation 추가
- `_drawMorphLabels()`: base/compare 각각의 label rotation을 개별 계산 후
  **shortest-path angular interpolation**으로 부드럽게 보간
- 180° 경계를 넘는 노드의 회전과 textAlign 전환도 smooth

### 3. Diff legend 위치 변경 (tree_chart.js)

`drawDiffLegend()`: 캔버스 왼쪽 위 (12, 12) → **오른쪽 아래**로 이동.
View-as-root breadcrumb (왼쪽 위)과 겹치는 문제 해소.

## 관련

- trilobase assertion DB v0.1.8 빌드에 반영
