# Bar Chart 서브뷰 + Statistics 탭 구조 개편

**날짜:** 2026-03-17
**작업 유형:** 기능 추가, 구조 개편
**버전:** scoda-engine 0.3.4, trilobase 0.3.3

---

## 배경

시대별 분류군 다양성을 한눈에 볼 수 있는 stacked bar chart를 추가하고,
기존 Timeline 탭을 Statistics 탭으로 재구성했다.

---

## 변경 내용

### 1. Bar Chart display 타입 추가 (scoda-engine)

**`app.js`:**
- `switchCompoundSubView()`에 `display === 'bar_chart'` 분기 추가
- `renderCompoundBarChartSubView()` 구현:
  - D3 stacked bar chart (X축: 카테고리, Y축: 값, 색상: 그룹별)
  - "Group by" 드롭다운으로 grouping rank 선택 (Order/Suborder/Superfamily/Family)
  - 툴팁 (hover 시 카테고리 + 그룹 + 값 표시)
  - HTML div 레전드 (차트 아래 배치, 스크롤 가능)
  - ResizeObserver 기반 반응형 리사이즈
- manifest 설정: `bar_chart_options` (x_key, x_order_key, group_key, value_key, grouping_param, grouping_ranks, default_grouping)

**`style.css`:**
- `.bar-chart-toolbar`, `.bar-chart-control`, `.bar-chart-select` — 툴바 스타일
- `.bar-chart-legend`, `.bar-legend-item`, `.bar-legend-swatch` — 레전드 스타일

### 2. Statistics 탭 구조 개편 (trilobase)

**기존:** Timeline 탭 → 단일 timeline 서브뷰 (axis_modes로 Geologic/Publication 전환)
**변경:** Statistics 탭 → 3개 서브탭:
- **Geologic Timeline** — 지질시대별 트리 애니메이션 (단일 axis_mode)
- **Publication Timeline** — 출판연도별 트리 애니메이션 (단일 axis_mode)
- **Diversity Chart** — stacked bar chart (시대별 × 분류군별 genus 수)

탭 순서도 변경: Tree → Comparison → Statistics

### 3. diversity_by_age 쿼리 (trilobase)

```sql
WITH RECURSIVE ancestors AS (
    -- genus만 대상으로 조상 탐색 시작
    SELECT e.child_id AS genus_id, e.parent_id AS ancestor_id
    FROM classification_edge_cache e
    JOIN taxon t ON t.id = e.child_id AND t.rank = 'Genus'
    WHERE e.profile_id = COALESCE(:profile_id, 1)
    UNION ALL ...
),
genus_group AS (
    -- genus → grouping rank 매핑 확정 (중복 방지)
    SELECT a.genus_id, grp.name AS group_name
    FROM ancestors a
    JOIN taxon grp ON grp.id = a.ancestor_id AND grp.rank = :grouping_rank
)
SELECT ... COUNT(DISTINCT g.id) AS count
FROM taxon g
JOIN classification_edge_cache ge ON ge.child_id = g.id ...  -- profile 내 genus만
JOIN temporal_code_mya tcm ON g.temporal_code = tcm.code
LEFT JOIN genus_group gg ON gg.genus_id = g.id
```

핵심 수정:
- CTE base case에 `JOIN taxon t ON t.rank = 'Genus'` — genus만 대상으로 재귀 시작
- `genus_group` 중간 CTE — 한 genus가 하나의 그룹에만 매핑되도록 확정
- `JOIN classification_edge_cache ge` — 해당 profile에 속한 genus만 카운트

### 4. Publication Timeline NULL guard 수정 (전체 패키지)

`taxonomy_tree_by_pubyear`, `tree_edges_by_pubyear` 쿼리에서:
- 기존: `AND t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value`
- 수정: `AND (:timeline_value IS NULL OR (t.year IS NOT NULL AND CAST(t.year AS INTEGER) <= :timeline_value))`
- 초기 로드 시 timeline_value가 NULL이면 전체 데이터 반환

적용 패키지: trilobase, brachiobase, chelicerobase, graptobase, ostracobase

### 5. 버전 업

- scoda-engine: 0.3.3 → 0.3.4
- trilobase: 0.3.2 → 0.3.3
- brachiobase, chelicerobase, graptobase, ostracobase: 각각 리빌드

---

## 영향 범위

**scoda-engine:**
- `scoda_engine/static/js/app.js`
- `scoda_engine/static/css/style.css`
- `pyproject.toml`, `scoda_engine/__init__.py`, `deploy/docker-compose.yml`

**trilobase (별도 저장소):**
- `scripts/build_trilobase_db.py` (쿼리 + manifest)
- `scripts/build_brachiobase_db.py` (쿼리 수정)
- `scripts/build_chelicerobase_db.py` (쿼리 수정)
- `scripts/build_graptobase_db.py` (쿼리 수정)
- `scripts/build_ostracobase_db.py` (쿼리 수정)
