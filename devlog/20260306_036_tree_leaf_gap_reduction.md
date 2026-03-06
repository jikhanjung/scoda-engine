# 036: Rectangular Tree Leaf 간격 축소

**Date:** 2026-03-06
**Status:** Done
**Related:** 032 (Rectangular Layout), 033 (Layout Refinements)

## 개요

Rectangular tree 레이아웃에서 leaf node 간 수직 간격이 넓어 트리가 불필요하게
길어지는 문제. LEAF_GAP을 절반으로 줄여 더 컴팩트한 표시.

## 변경 사항

- `scoda_engine/static/js/tree_chart.js`: `LEAF_GAP` 12px → 6px
- Desktop 버전 0.1.6 → 0.1.7
