# P28 — Timeline 구현 계획 (상세)

**날짜**: 2026-03-14
**선행 문서**: `20260313_P28_geologic_time_and_publication_timeline.md`

---

## 설계 원칙

SCODA Engine은 도메인 코드를 포함하지 않는다. "지질시대", "출판 연도" 등의 개념은
엔진이 알 필요 없으며, 엔진은 **범용 타임라인 슬라이더 메커니즘**만 제공한다.

- 시간축(axis)의 정의: `.scoda` 패키지의 `ui_manifest` → `timeline_options`
- 각 스텝의 데이터: `.scoda` 패키지의 `ui_queries` (SQL)
- 누적/스냅샷 여부: 쿼리 작성 방식으로 결정 (엔진 변경 불필요)

---

## UI 구조

TreeChart compound view 내 서브탭으로 구성:

```
[Classification ▾]  ← compound view 탭
  [Tree] [Side-by-Side] [Diff] [Timeline]  ← 서브탭
                                    ↓
                          [드롭다운: 축 모드 선택]
                          [슬라이더: 스텝 선택]
                          [Play ▶ | Pause ⏸ | 속도 | Step ▼]
```

축 모드 전환은 **드롭다운**으로 구현.

---

## Manifest 스키마

### compound sub_view 정의

```json
{
  "timeline": {
    "display": "tree_chart_timeline",
    "title": "Timeline",
    "source_query": "taxonomy_tree_by_timeline",
    "hierarchy_options": {
      "id_key": "id",
      "parent_key": "parent_id",
      "label_key": "name",
      "rank_key": "rank"
    },
    "tree_chart_options": {
      "default_layout": "radial",
      "rank_radius": { ... },
      "edge_query": "tree_edges_by_timeline",
      "edge_params": { "timeline_value": "$timeline_value" }
    },
    "timeline_options": {
      "param_name": "timeline_value",
      "step_size_param": "timeline_step",
      "default_step_size": 1,
      "axis_modes": [
        {
          "key": "geologic",
          "label": "Geologic Time",
          "axis_query": "geologic_periods",
          "value_key": "id",
          "label_key": "name",
          "order_key": "sort_order"
        },
        {
          "key": "pubyear",
          "label": "Publication Year",
          "axis_query": "publication_years",
          "value_key": "year",
          "label_key": "year",
          "order_key": "year"
        }
      ]
    }
  }
}
```

### .scoda 쿼리 예시

```sql
-- geologic_periods: 축 스텝 목록
SELECT id, name, sort_order FROM time_periods ORDER BY sort_order;

-- publication_years: 축 스텝 목록
SELECT DISTINCT year, year AS label FROM references
WHERE year IS NOT NULL ORDER BY year;

-- taxonomy_tree_by_timeline: 필터된 트리 (누적 모드 예시)
SELECT id, name, rank, parent_id
FROM taxonomy
WHERE publication_year <= :timeline_value;

-- taxonomy_tree_by_timeline: 스냅샷 모드 예시
SELECT id, name, rank, parent_id
FROM taxonomy
WHERE geologic_period = :timeline_value;
```

---

## 구현 단계

### Phase 1: 정적 타임라인 (슬라이더 → 트리 재로드)

스텝 변경 시 트리를 즉시 다시 그린다 (애니메이션 없이).

#### 1-1. `app.js` — `renderCompoundTimelineSubView()`

`switchCompoundSubView()`에 `"tree_chart_timeline"` 분기 추가.

```
renderCompoundTimelineSubView(subKey, subView, containerEl):
  1. timeline_options 파싱
  2. 축 모드 드롭다운 렌더링 (axis_modes)
  3. 드롭다운 change → loadTimelineAxis(mode) 호출
  4. TreeChartInstance 생성 + canvas 배치
```

#### 1-2. `app.js` — `loadTimelineAxis(mode)`

```
loadTimelineAxis(mode):
  1. mode.axis_query 실행 → 스텝 목록 취득
  2. 슬라이더 min/max/step 설정
  3. 슬라이더 라벨 업데이트
  4. 첫 번째 스텝으로 트리 로드
```

#### 1-3. `tree_chart.js` — 슬라이더 연동

기존 `overrideParams` 메커니즘 활용:

```
슬라이더 input 이벤트:
  1. overrideParams[param_name] = steps[sliderValue].value
  2. buildHierarchy(view) 재실행
  3. computeLayout() + render()
```

#### 1-4. Step Size 설정

슬라이더 옆에 step size 입력 (기본값: `default_step_size`).
출판 연도처럼 스텝이 많을 때 "10년 단위" 등으로 건너뛰기 가능.

```
Step size 변경:
  1. 원본 steps 배열에서 step_size 간격으로 필터
  2. 슬라이더 max 재설정
  3. 현재 위치 가장 가까운 스텝으로 스냅
```

### Phase 2: 연쇄 Morph 애니메이션

인접 스텝 간 morph를 연결하여 자동 재생.

#### 2-1. `tree_chart.js` — `loadTimelineMorph(fromStep, toStep)`

```
loadTimelineMorph(fromStep, toStep):
  1. overrideParams = { [param_name]: fromStep.value }
  2. buildHierarchy(view) → snapshotPositions/Links → base 저장
  3. overrideParams = { [param_name]: toStep.value }
  4. buildHierarchy(view) → snapshotPositions/Links → compare 저장
  5. 기존 _morphBasePositions / _morphComparePositions에 세팅
```

#### 2-2. `tree_chart.js` — `playTimeline(startIdx, endIdx, speed)`

```
playTimeline(startIdx, endIdx, speed):
  currentIdx = startIdx
  loop:
    1. loadTimelineMorph(steps[currentIdx], steps[currentIdx + stepSize])
    2. renderMorphFrame(0→1) 애니메이션 실행
       - 스텝 간 변화가 적으면 duration 짧게 (기본 1600ms / speed)
    3. 완료 콜백 → currentIdx += stepSize
    4. 슬라이더 위치 + 라벨 업데이트
    5. currentIdx >= endIdx 이면 정지
```

#### 2-3. Look-ahead 캐싱

```
playTimeline 내부:
  현재 스텝 morph 실행 중에 다음 스텝의 트리 데이터를 미리 fetch.
  fetchQuery()는 queryCache에 자동 저장되므로,
  다음 buildHierarchy() 호출 시 캐시 히트.
```

#### 2-4. 컨트롤 바 UI

기존 morph 컨트롤 패턴 재활용:

```
[◀ Rewind] [▶ Play / ⏸ Pause] [Step ▸] [Speed: 1x ▾]
[|----●-----------| 슬라이더 ]  [Step size: 1 ▾]
[Cambrian ← 현재 스텝 라벨 →]
```

- Rewind: 첫 스텝으로
- Play/Pause: 자동 재생 토글
- Step: 다음 스텝 하나만 morph
- Speed: 0.5x / 1x / 2x / 4x
- 슬라이더: 드래그로 즉시 이동 (애니메이션 없이)

### Phase 3: 다듬기

- Removed 패널: 이전 스텝 대비 사라진 노드 표시 (기존 `_updateRemovedPanel()` 재활용)
- Watch 기능: 타임라인 모드에서도 watched 노드 추적
- Depth slider: 타임라인 모드에서도 visible depth 조절 가능
- 동영상 다운로드: 전체 타임라인 재생을 녹화 (기존 record 패턴 확장)

---

## 수정 파일 요약

| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `scoda_engine/static/js/app.js` | 1 | `renderCompoundTimelineSubView()`, 축 모드 드롭다운, 슬라이더 UI |
| `scoda_engine/static/js/tree_chart.js` | 1,2 | 슬라이더 연동, `loadTimelineMorph()`, `playTimeline()`, look-ahead |
| `scoda_engine/static/css/style.css` | 1 | 타임라인 컨트롤 바 스타일 |
| `scoda_engine/app.py` | — | 변경 없음 (기존 `/api/queries/<name>/execute` 그대로 사용) |
| `.scoda` 패키지 | — | 엔진 외부: manifest + 쿼리 추가 (도메인 측 작업) |

---

## 작업 순서

| # | 작업 | 의존 | 규모 |
|---|------|------|------|
| 1 | `app.js`: timeline 서브뷰 분기 + 축 모드 드롭다운 + 슬라이더 UI | — | 중 |
| 2 | `tree_chart.js`: 슬라이더 → overrideParams → 트리 재로드 | 1 | 중 |
| 3 | Step size 설정 UI | 2 | 소 |
| 4 | `tree_chart.js`: `loadTimelineMorph()` + `playTimeline()` | 2 | 중 |
| 5 | 컨트롤 바 (Play/Pause/Step/Speed/Rewind) | 4 | 중 |
| 6 | Look-ahead 캐싱 | 4 | 소 |
| 7 | Removed 패널 + Watch + Depth 연동 | 5 | 소 |
| 8 | 스타일링 + UX 다듬기 | 전체 | 소 |

---

## 도메인 측 선행 작업 (.scoda 패키지)

엔진 구현과 병렬로 진행 가능:

1. DB 스키마 확인: `time_periods` 테이블, `references.year` 컬럼 존재 여부
2. 축 쿼리 작성: `geologic_periods`, `publication_years`
3. 필터 쿼리 작성: `taxonomy_tree_by_timeline`, `tree_edges_by_timeline`
4. `ui_manifest`에 timeline 서브뷰 추가

---

## 열린 질문 (해결됨)

| 질문 | 결정 |
|------|------|
| 축 모드 전환 UI | 드롭다운 |
| 스텝이 많을 때 (174개 등) | 스텝 간 변화가 적으면 morph duration 짧게 + step size 설정으로 건너뛰기 |
| 데이터 로딩 | On-demand + look-ahead 캐싱 |
