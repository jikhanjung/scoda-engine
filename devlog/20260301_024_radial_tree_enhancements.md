# 20260301_024 Radial Tree 기능 고도화

**날짜**: 2026-03-01
**기반 커밋**: `4b0b85e` (P20 radial hierarchy v0.1.3)
**상태**: 미커밋

## 요약

P20에서 구현한 radial hierarchy display의 다수 버그를 수정하고, 사용성 개선 기능을 추가함.

## 변경 파일

| 파일 | 내용 |
|------|------|
| `scoda_engine/static/js/radial.js` | 대폭 개선 (120줄 → 730줄+) |
| `scoda_engine/static/js/app.js` | `fetchQuery()` 파라미터 지원 |
| `scoda_engine/static/css/style.css` | 컨텍스트 메뉴 스타일 추가 |
| `scoda_engine/templates/index.html` | 캐시 버스팅, 컨텍스트 메뉴 요소 |
| `scoda_engine/app.py` | 캐시 버스팅 (`cache_bust` 변수) |
| `.github/workflows/pages.yml` | hub index 생성 시 `--all` 플래그 추가 |

## 주요 변경 사항

### 1. 버그 수정

- **fetchQuery 파라미터 전달**: `edge_params`를 URL 쿼리로 전달하도록 수정
- **edge key 설정**: `edge_child_key` / `edge_parent_key` 설정 가능하게 (기본값 `child_id` / `parent_id`)
- **Map 키 타입 불일치**: `String()` 변환으로 number/string 타입 불일치 해결
- **다중 루트 처리**: `__virtual_root__` 가상 루트 삽입으로 d3.stratify() 호환
- **캐시 문제**: Jinja2 `?v={{ cache_bust }}` (타임스탬프) 로 정적 파일 캐시 방지

### 2. 레이아웃 개선

- **d3.cluster → d3.tree 전환**: 같은 rank 노드가 같은 동심원에 위치하도록 변경
- **rank_radius 오버라이드**: manifest에서 rank별 반지름 비율 지정 가능 (e.g. Class: 0.10, Family: 0.70)
- **계층적 separation 함수**: LCA(최소 공통 조상) 깊이 기반 각도 간격 부여
- **정렬 순서 개선**: 비-leaf rank를 먼저, leaf rank를 나중에 (각각 알파벳순)

### 3. Pruned Tree (가지치기 트리)

- `radialFullRoot` (전체 트리) + `radialPrunedRoot` (leaf rank 제거) 두 트리 미리 생성
- Depth 토글 버튼으로 전환 (기본: pruned 상태로 시작)
- 전환 시 레이아웃 전체 재계산

### 4. 노드 Collapse/Expand

- 내부 노드 클릭 → 자식 접기/펼치기 (`node._children` ↔ `node.children`)
- 접힌 노드: 외곽 원 + "+" 표시
- 접힌 노드에 angular weight (+3) 부여하여 인접 노드와 겹침 방지
- 접기/펼기 후 레이아웃 재계산

### 5. Subtree Root (서브트리 보기)

- 특정 taxon을 루트로 하는 서브트리 뷰 지원
- `buildSubtreeFromNode()`: 원본 트리에서 deep copy하여 독립 서브트리 생성
- Breadcrumb 네비게이션: `All / Class / Order / ...` 경로 표시, 클릭으로 상위 이동
- Depth 토글/Reset과 서브트리 상태 연동

### 6. 우클릭 컨텍스트 메뉴

- 더블클릭 대신 우클릭 컨텍스트 메뉴 채택 (클릭 이벤트 충돌 회피)
- 메뉴 항목:
  - **View as root**: 서브트리 보기 (내부 노드)
  - **Expand / Collapse**: 접기/펼치기 (내부 노드)
  - **Zoom to**: 해당 노드로 확대
  - **Detail**: 상세 모달 (leaf 노드)
- 헤더에 rank + label 표시
- 뷰포트 밖으로 나가지 않도록 위치 보정

### 7. 라벨 표시 개선

- `isLeafByRank()` 함수로 rank 기반 leaf 판별 (d3 구조 대신)
- 비-leaf rank는 항상 라벨 표시
- leaf rank(Genus)는 줌 레벨 2 이상 + 뷰포트 내에서 표시 (기존 4 → 2로 완화)
- 고정 폰트 크기 (줌에 따라 축소되지 않음)
- rank별 폰트 크기: Class/Order 12px, Family 10px, Genus 9px
- maxLabels 150 → 500

### 8. 고아 노드 필터링

- edge에 포함되지 않는 고아 노드(invalid genus 등)를 JS 측에서 제거
- edge의 child/parent 목록과 대조하여 소속 없는 노드 필터 아웃

### 9. 줌 연동 라벨 크기 조정

- 기존: 줌 레벨에 관계없이 라벨 폰트 크기 고정 (Genus 9px, Family 10px 등)
- 변경: 줌 50% 비율로 라벨 크기가 함께 증가 (`zoomScale = min(0.5 + 0.5 * k, 4)`)
  - k=1 (기본): 1.0x (변화 없음)
  - k=2: 1.5x (Genus 9px → 13.5px)
  - k=4: 2.5x (Genus 9px → 22.5px)
  - k=7+: 4.0x 상한 (Genus 9px → 36px)
- 라벨 offset(노드↔텍스트 간격)도 동일 비율로 조정하여 겹침 방지

## 비고

- trilobase 쪽 `scripts/create_assertion_db.py`에서도 관련 변경 있음 (DB 컬럼명, 쿼리 필터, rank_radius 설정 등) — 별도 기록 필요
- `console.log` 디버그 출력이 일부 남아 있음 (정리 필요)
