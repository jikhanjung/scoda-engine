# 028: Composite Detail Bugfix + Tree Chart Visible Depth Slider

**날짜:** 2026-03-13

## 변경 내용

### 1. Composite Detail 엔드포인트 버그 수정 (`app.py`)

**문제:**
- `api_composite_detail`에서 메인 쿼리 실행 시 `source_param`만 전달하고, 다른 바인딩 파라미터(예: `profile_id`)를 전달하지 않아 `COALESCE(:profile_id, 1)` 패턴이 실패
- 에러 체크 순서가 잘못되어 쿼리 에러(`{'error': '...'}`)가 404 Not Found로 감춰짐

**수정:**
1. `_execute_query()`: `params_json`에 선언된 파라미터 중 누락된 것을 `None`으로 자동 채움 → `COALESCE(:param, default)` 정상 동작
2. `api_composite_detail` 메인 쿼리: `request.query_params` 전체를 함께 전달
3. `api_composite_detail` sub-query: 동일하게 `request.query_params` 포워딩
4. 에러 체크(`'error' in result`)를 `row_count == 0` 체크보다 앞으로 이동

### 2. Tree Chart Visible Depth Slider (`tree_chart.js`, `style.css`)

**기능:** 트리 차트에서 leaf rank부터 원하는 rank까지 숨길 수 있는 슬라이더.

**UI:**
- 툴바 우상단에 톱니바퀴(gear) 아이콘 추가
- 클릭 시 팝업에 "Visible depth" 슬라이더 표시
- 슬라이더는 `rank_radius` 키 순서(root→leaf) 기반
- 최대값: `All (Genus)` — 모든 rank 표시
- 줄이면: `→ Family` 등 현재 보이는 가장 깊은 rank 표시

**동작:**
- 숨겨진 rank의 노드, 텍스트 라벨, 연결선 모두 숨김
- **레이아웃 재계산**: depth 변경 시 `computeLayout()` 재실행, 숨겨진 자식이 있는 노드를 leaf처럼 취급하여 나머지 노드를 균등 분포
- Radial / Rectangular 레이아웃 모두 지원
- Morph 애니메이션, Side-by-Side 뷰 동기화 지원

**구현 상세:**
- `_rankOrder`: `rank_radius` 키에서 추출한 rank 순서 배열
- `visibleDepth`: 표시할 rank 수 (0 = 전체)
- `_hiddenRanks`: 숨길 rank Set
- `_isRankHidden(node)`: 노드의 rank가 숨겨져야 하는지 체크
- `setVisibleDepth(depth)`: depth 설정 + 레이아웃 재계산 + 렌더링
- `onVisibleDepthSync`: Side-by-Side 인스턴스 간 동기화 콜백

## 수정 파일

| 파일 | 변경 |
|------|------|
| `scoda_engine/app.py` | composite 엔드포인트 버그 수정 3건 |
| `scoda_engine/static/js/tree_chart.js` | visible depth 슬라이더 + 레이아웃 재계산 |
| `scoda_engine/static/css/style.css` | 설정 팝업 스타일 |

## 테스트

- `test_runtime.py`: 223 passed
- `test_crud.py`: 27 passed
- 총 250 passed
