# Boolean 표시 라벨 통일 및 커스텀 지원

**Date:** 2026-02-22
**Type:** Fix / Enhancement

---

## 문제

Boolean 값 표시가 렌더링 위치마다 다르고, 커스텀 라벨을 지원하지 않는 곳이 있었음:

- `formatFieldValue()` (detail field_grid): `true_label`/`false_label` 지원, 기본값 "Yes"/"No"
- `renderTableViewRows()` (table view): 하드코딩 "Yes"/"No", 커스텀 라벨 미지원
- `renderTreeItemTable()` (tree item list): boolean 처리 자체가 없음
- `renderLinkedTable()` (detail linked_table): 하드코딩 "Yes"/"No", 커스텀 라벨 미지원

## 변경 내용

### 1. 전역 기본 상수 추가

```javascript
const BOOLEAN_TRUE_LABEL = 'True';
const BOOLEAN_FALSE_LABEL = 'False';
```

기본값을 "Yes"/"No"에서 "True"/"False"로 변경하고 상수로 통일.

### 2. 모든 boolean 렌더링 위치에 커스텀 라벨 지원

| 위치 | 변경 |
|------|------|
| `renderTableViewRows()` | `col.true_label`/`col.false_label` 지원 추가 |
| `renderTreeItemTable()` | `col.format === 'boolean'` 분기 추가 + 커스텀 라벨 |
| `renderLinkedTable()` | `col.true_label`/`col.false_label` 지원 추가 |
| `formatFieldValue()` | 기본값을 상수로 교체 |

### 3. manifest 사용 예

```json
{
  "key": "is_valid",
  "label": "Valid",
  "type": "boolean",
  "true_label": "Valid",
  "false_label": "Invalid"
}
```

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/static/js/app.js` | boolean 기본 라벨 상수화 + 4곳 통일 |
