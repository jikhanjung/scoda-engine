# P26: Tree Search 개선 + Watch 기능 + Removed Taxa 목록

**날짜**: 2026-03-11
**관련**: trilobase P84

## 배경

현재 Tree Chart 뷰에 "Search nodes" 검색창이 있으나 제대로 작동하지 않음.
검색·관찰 기능을 개선하여 대규모 트리에서 관심 분류군을 추적할 수 있도록 한다.

## 기능 목록

### 1. Search Nodes 수정
- 현재 검색창이 제대로 작동하지 않는 문제 해결
- 검색 결과가 현재 캔버스 뷰포트 안에 있으면 해당 노드에 팝업으로 정보 표시

### 2. Node Context Menu — Watch 추가
- 노드 우클릭 시 컨텍스트 메뉴에 "Watch" 항목 추가
- 이미 Watch 중이면 "Unwatch"로 토글

### 3. Watch 목록 패널
- 캔버스 우상단, 기존 컨트롤(검색창 등) 아래에 Watch 중인 taxa 목록 표시
- 목록에서 항목 클릭 시 해당 노드로 이동(포커스)
- 항목 옆에 제거(×) 버튼

### 4. Watch 노드 확대 렌더링
- Watch 중인 노드: **2× 크기**로 렌더링
- Watch 노드의 parent + children: **1.5× 크기**로 렌더링
- 확대는 노드 원(circle)과 라벨 모두에 적용

### 5. Diff Tree / Animation — Removed Taxa 목록
- Diff Tree나 Animation 뷰에서 removed 상태인 taxa 목록을 별도 패널로 표시
- 트리에서 사라진 분류군을 한눈에 확인할 수 있도록 함

## 구현 위치

- Tree Chart 컴포넌트: `spa/components/` 내 tree chart 관련 파일
- 데이터/쿼리 변경: 없음 (순수 프론트엔드 기능)

## 우선순위

1. Search Nodes 수정 (기존 버그 수정)
2. Watch + 확대 렌더링 (신규 기능)
3. Watch 목록 패널 (UI 추가)
4. Removed Taxa 목록 (Diff/Animation 뷰)
