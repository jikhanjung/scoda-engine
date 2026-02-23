# S6. label_map 동적 컬럼 label 지원

**날짜**: 2026-02-23
**관련**: trilobase devlog 089

## 배경

trilobase의 manifest에서 `linked_table` 컬럼에 `label_map` 속성이 추가됨.
행 데이터의 특정 필드 값에 따라 테이블 헤더 label을 동적으로 결정하는 기능.

## 변경 내용

### `scoda_engine/static/js/app.js` — `renderLinkedTable()`

헤더 렌더링 시 `label_map` 해석 로직 추가:

```javascript
columns.forEach(col => {
    let label = col.label;
    if (col.label_map && rows.length > 0) {
        const values = new Set(rows.map(r => r[col.label_map.key]));
        if (values.size === 1) {
            label = col.label_map.map[values.values().next().value] || label;
        }
    }
    html += `<th>${label}</th>`;
});
```

**동작 규칙:**
- 모든 행의 지정 필드값이 동일 → 매핑된 label 사용
- 혼합 → `col.label` fallback (하위 호환)

### label_map 스키마

```json
{
  "label_map": {
    "key": "opinion_type",
    "map": {
      "PLACED_IN": "Proposed Parent",
      "SPELLING_OF": "Correct Spelling",
      "SYNONYM_OF": "Valid Name"
    }
  }
}
```

## 테스트

- scoda-engine: 225 passed
- trilobase: 101 passed
