# 030 — Timeline Sub-view 구현 (Phase 1 + 2)

**날짜**: 2026-03-14
**관련**: P28

## 개요

Compound view 내에 `tree_chart_timeline` 서브뷰 타입을 구현.
시간축 슬라이더로 트리를 탐색하고, 스텝 간 morph 애니메이션으로 전환하는 기능.

## 구현 내용

### Phase 1: 정적 타임라인 (슬라이더 → 트리 즉시 재로드)

- `app.js`: `renderCompoundTimelineSubView()` 함수 추가
- `switchCompoundSubView()`에 `tree_chart_timeline` 분기 추가
- 축 모드 드롭다운 (`timeline_options.axis_modes`) — 복수 시간축 전환
- `axis_query` 실행 → 슬라이더 스텝 목록 자동 구성
- Step size 설정 (건너뛰기) — 스텝이 많을 때 N단위로 필터
- 슬라이더 드래그 → `overrideParams[param_name]` 갱신 → 트리 즉시 재로드

### Phase 2: 연쇄 Morph 애니메이션

- `morphToStep(fromIdx, toIdx, speed)` — 두 스텝 간 morph 애니메이션
  - 기존 `snapshotPositions/Links` + `renderMorphFrame(t)` 재활용
  - 1600ms/speed 기본 duration (기존 morph의 절반 — 스텝 간 변화가 적으므로)
- `playTimeline(forward)` — 연쇄 morph 자동 재생 (while 루프)
- Look-ahead 캐싱: 현재 morph 중 다음 스텝 데이터 미리 fetch
- Removed 패널 연동: `_updateRemovedPanel()` 호출

### 컨트롤 바 UI

```
[드롭다운: 축 모드] [Step: N]
[⏮][◀][⏸][▶][⏭][⏩] [1/30] [|---●------|] [Cambrian] [1x ▾]
```

- Rewind / Play backward / Pause / Play forward / Fast forward / Step forward
- 스텝 카운터 (현재/전체)
- 슬라이더 (즉시 이동)
- 현재 스텝 라벨
- 속도 선택 (0.5x / 1x / 2x / 4x)

## Manifest 스키마

`.scoda` 패키지의 `ui_manifest`에서 다음과 같이 정의:

```json
{
  "timeline": {
    "display": "tree_chart_timeline",
    "title": "Timeline",
    "source_query": "taxonomy_tree_filtered",
    "hierarchy_options": { ... },
    "tree_chart_options": { ... },
    "timeline_options": {
      "param_name": "timeline_value",
      "default_step_size": 1,
      "axis_modes": [
        {
          "key": "geologic",
          "label": "Geologic Time",
          "axis_query": "geologic_periods",
          "value_key": "id",
          "label_key": "name",
          "order_key": "sort_order"
        }
      ]
    }
  }
}
```

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/static/js/app.js` | `renderCompoundTimelineSubView()` ~340행 추가, `switchCompoundSubView` 분기 추가 |
| `scoda_engine/static/css/style.css` | `.timeline-controls` 관련 스타일 ~100행 추가 |

## 테스트

- 303 tests 통과 (프론트엔드 변경, 백엔드 영향 없음)
- 기능 테스트는 `.scoda` 패키지에 timeline 관련 쿼리 추가 후 수행 필요

## 도메인 측 남은 작업

엔진 측 구현은 완료. `.scoda` 패키지에서 다음을 추가해야 실제 동작:
1. `ui_manifest`에 timeline 서브뷰 정의
2. `ui_queries`에 축 쿼리 (`geologic_periods`, `publication_years` 등)
3. `ui_queries`에 필터 쿼리 (`taxonomy_tree_filtered` — `:timeline_value` 파라미터 사용)
