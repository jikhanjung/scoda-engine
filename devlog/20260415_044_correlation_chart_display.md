# 2026-04-15 | Correlation Chart Display Type

## Summary

Generic viewer에 새로운 display type `correlation`을 추가했다. Pre-computed rowspan 데이터를 기반으로 두 개의 병렬 계층(예: 두 층군의 Formation-Biozone)을 나란히 보여주는 correlation table을 렌더링한다.

## Background

kstrati 프로젝트(한국 태백산분지 층서 데이터)에서 태백층군과 영월층군의 litho-/biostratigraphic correlation chart가 필요했다. 기존 `nested_table` display는 단일 계층(ICS chart)에 적합하지만, 두 개의 독립적인 Formation-Biozone 시퀀스를 시간축으로 정렬하여 나란히 보여주는 용도에는 맞지 않았다.

## Changes

### app.js
- `renderCorrelationView(viewKey)` 함수 추가
  - `source_query`에서 pre-computed 행 데이터를 fetch
  - `correlation_display.column_groups`로 상단 그룹 헤더 렌더링 (예: AGE | Taebaek Group | Yeongwol Group)
  - `correlation_display.columns`로 개별 컬럼 정의
  - 각 컬럼의 `rowspan_key`를 참조하여 rowspan 적용 (0이면 skip)
- `border_follow` 속성: biozone 컬럼의 top border를 대응하는 formation의 rowspan에 연동. 같은 층 내 biozone 사이의 가로선을 제거하되 층 경계에서는 유지
- `border_bottom_values` 속성: 특정 biozone 값 아래에만 bottom border 표시 (예: stage 경계 표현)
- View switching에 `display === 'correlation'` 분기 추가 (view-chart 컨테이너 재사용)

### style.css
- `.correlation-chart`: table-layout auto
- `.corr-period`: 세로 쓰기 (writing-mode: vertical-lr)
- `.corr-stage`: 회색 배경, 중앙 정렬
- `.corr-fm`: Formation 셀, 좌측 굵은 테두리
- `.corr-bz`: Biozone 셀, 이탤릭, 중앙 정렬
- `.corr-bz-cont`: (unused, inline style로 대체) — border-collapse: collapse 환경에서 `border-top: hidden` inline style 사용
- `.corr-empty`: 빗금 패턴 (현재 미사용)

## Manifest Example

```json
{
  "type": "hierarchy",
  "display": "correlation",
  "source_query": "correlation_chart",
  "correlation_display": {
    "column_groups": [
      {"label": "AGE", "colspan": 2},
      {"label": "Taebaek Group", "colspan": 2},
      {"label": "Yeongwol Group", "colspan": 2}
    ],
    "columns": [
      {"key": "period", "rowspan_key": "period_rowspan", "css_class": "corr-period"},
      {"key": "stage", "rowspan_key": "stage_rowspan", "css_class": "corr-stage"},
      {"key": "taebaek_fm", "rowspan_key": "taebaek_fm_rowspan", "css_class": "corr-fm"},
      {"key": "taebaek_bz", "css_class": "corr-bz", "italic": true,
       "border_follow": "taebaek_fm_rowspan",
       "border_bottom_values": ["Fenghuangella"]},
      {"key": "yeongwol_fm", "rowspan_key": "yeongwol_fm_rowspan", "css_class": "corr-fm"},
      {"key": "yeongwol_bz", "css_class": "corr-bz", "italic": true,
       "border_follow": "yeongwol_fm_rowspan",
       "border_bottom_values": ["Glyptagnostus reticulatus"]}
    ]
  }
}
```

## Data Contract

Query result rows must include:
- Display columns (e.g. `period`, `stage`, `taebaek_fm`, `taebaek_bz`, ...)
- Rowspan columns with `_rowspan` suffix (e.g. `period_rowspan`, `taebaek_fm_rowspan`, ...)
- Rowspan value: >0 = render cell with that rowspan, 0 = skip (covered by previous row)
