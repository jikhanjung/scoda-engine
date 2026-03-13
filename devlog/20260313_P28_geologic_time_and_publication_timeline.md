# P28 — 지질시대별 분류 변화 + 논문 출판 연도 타임라인

## UI 구조 결정

### Timeline 탭 위치

두 가지 옵션:

**A. TreeChart 서브메뉴** — 현재 이미 `compound` view type(탭 안에 서브탭)이 구현되어 있음.
`tree_chart` 탭을 compound로 전환하면 서브탭으로 `Tree | Timeline` 구성 가능.

```
[TreeChart 탭]
  └── [Tree] [Timeline ▾]
                └── 지질시대 / 출판 연도 (토글 또는 2개 서브탭)
```

**B. 독립 탭** — `ui_manifest`에 `type: timeline`인 별도 탭을 추가.
TreeChart와 완전히 분리, 탭 바가 넓어짐.

### 결론 (잠정)
**A안 (TreeChart 서브메뉴)** 채택 방향.
- Timeline은 TreeChart의 "다른 축으로 보는 트리"이므로 의미상 동일 탭이 적합
- compound 패턴이 이미 구현되어 있어 추가 뼈대 불필요
- 지질시대 / 출판 연도는 Timeline 서브탭 안의 **라디오 버튼 또는 드롭다운**으로 전환

---

## 배경

현재 Diff Tree / Side-by-Side Tree는 **프로파일(분류 체계)** 간 변화를 비교하는 기능이다.
두 가지 추가 뷰가 필요하다:

1. **지질시대 타임라인** — 캄브리아기·오르도비스기 등 지질 시대별로 분류가 어떻게 달라지는지
2. **논문 출판 연도 타임라인** — 각 분류군이 기재된 논문의 출판 연도 순서로 분류 변화를 보여주는 뷰

---

## Feature 1: 지질시대별 분류 변화 (Geologic Time View)

### 목표
- X축(또는 슬라이더): 지질 시대 (Cambrian → Ordovician → Silurian …)
- 각 시대마다 해당 시대에 생존했던 분류군의 트리를 렌더링
- 시대가 달라질 때 트리 노드의 추가/소멸/이동을 애니메이션으로 표현

### 구현 방향
- DB에 `geologic_occurrence` 테이블 또는 기존 `entries` 테이블의 시대 컬럼 활용
- 지질 시대 순서는 별도 lookup 테이블(`time_periods`)로 관리
- 뷰 매니페스트에 `type: geologic_timeline` 추가하거나, 기존 tree_chart에 `filter_axis: time_period` 옵션 추가
- 슬라이더 UI는 P27에서 구현된 `depth_slider` 패턴 재활용 가능

### 열린 질문
- 시대 경계를 엄격히 적용할지, 범위(from~to) 필터로 처리할지
- 복수 시대에 걸쳐 생존하는 분류군은 구간 내 모든 슬라이더 위치에서 표시

---

## Feature 2: 논문 출판 연도 타임라인 (Publication Year Timeline)

### 목표
- 분류군이 **기재(記載)된 논문의 출판 연도**를 기준으로 분류 변화를 타임라인으로 시각화
- "이 논문이 나오기 전까지 분류는 어떻게 생겼는가" 를 연도 슬라이더로 탐색

### 구현 방향
- `references` 테이블의 `year` 컬럼 + `items` ↔ `references` 연결 활용
- 슬라이더를 연도(예: 1850~2024)로 설정, 선택 연도까지 출판된 논문만 반영한 트리 렌더링
- 기존 Diff Tree와 달리 "누적(cumulative)" 뷰: 연도가 올라갈수록 노드가 추가됨

### 열린 질문
- 같은 연도에 서로 모순되는 분류가 나온 경우 처리 방법
- 분류 변경을 명시하는 별도 `classification_event` 테이블이 필요한지, 아니면 기존 스키마로 충분한지

---

## 우선순위 및 의존성

| 순서 | 항목 | 의존 |
|------|------|------|
| 1 | DB 스키마 확인 / `time_periods` + `references.year` 데이터 정비 | — |
| 2 | Feature 1: 지질시대 슬라이더 + 필터 쿼리 | P27 depth_slider |
| 3 | Feature 2: 출판 연도 슬라이더 + 누적 쿼리 | Feature 1 패턴 재활용 |
| 4 | 두 뷰 모두 애니메이션 전환 (기존 tree_chart.js morph 로직 확장) | P25 morph |

---

## 관련 파일 (예상)

- `scoda_engine/static/js/tree_chart.js` — 슬라이더·필터 로직 추가
- `scoda_engine/app.py` — 새 API 엔드포인트 or 기존 `/api/query/<name>` 활용
- `scoda_engine/templates/index.html` — 새 컨트롤 UI
- `.scoda` 패키지 내 `ui_manifest` — 새 view type 정의
