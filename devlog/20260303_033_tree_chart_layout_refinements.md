# 033: Tree Chart Layout Refinements

**Date:** 2026-03-03
**Status:** Done
**Related:** P23, 032 (Tree Chart Rectangular Layout)

## 개요

P23 초기 구현(032) 이후 rectangular/radial 레이아웃의 렌더링 품질 개선.

## 변경 사항

### 1. Rectangular 라벨 위치 분기

- Leaf 노드: 노드 오른쪽에 `text-anchor: start`
- Internal 노드: 노드 왼쪽 어깨(top-left shoulder)에 `text-anchor: end`
- `isRectLeaf()` 헬퍼: rank 기반 leaf OR structural leaf (자식 없음) 모두 처리
  — depth toggle로 pruned tree 볼 때도 말단 노드 라벨이 정상 위치

### 2. 같은 rank 노드 X 위치 정렬

`computeCladogramLayout()`에서 d3.tree() 이후 rank별 X 정렬:
- `rank_radius` 있으면: 비율값 * treeW
- 없으면: 각 rank의 평균 depth 기준 자동 균등 배치

Radial 모드의 `rank_radius` 설정을 rectangular에서도 동일하게 재활용.

### 3. Bottom-up 레이아웃 (d3.tree 대체)

d3.tree()의 separation 함수가 subtree 전체 높이를 고려하지 않아
다른 부모의 leaf 노드들이 겹치는 문제 해결.

**Rectangular** (`computeCladogramLayout`):
- d3.tree() 제거, 직접 bottom-up 레이아웃
- Leaf에 순서대로 Y 슬롯 배정 (LEAF_GAP=24px, collapsed=48px)
- Sibling subtree 사이 추가 간격 (SUBTREE_GAP=8px)
- Internal 노드는 첫째~마지막 child의 Y 중앙

**Radial** (`computeRadialLayout`):
- 동일한 bottom-up 방식으로 각도 배정
- LEAF_GAP_DEG=2°, SUBTREE_GAP_DEG=1°, collapsed=4°
- 전체를 360°로 정규화
- 기존 MIN_SPACING (최소 arc 거리 20px) 보정 유지

### 4. Desktop v0.1.5

버전 업: `scoda_engine/__init__.py` + `pyproject.toml`

## 기술 결정

- Bottom-up 레이아웃은 모든 leaf가 고유 슬롯을 받으므로 겹침이 원리적으로 불가능
- Radial/rectangular 모두 같은 원리로 통일하여 모드 전환 시 일관된 결과
- d3.tree()의 Reingold-Tilford 알고리즘 대비 미관은 약간 다를 수 있으나, 겹침 방지가 우선
