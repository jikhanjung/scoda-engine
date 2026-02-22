# P11: Tree Snapshot Design v1 검토 의견

**Date:** 2026-02-22
**Type:** Design Review
**대상 문서:** `docs/Trilobase_Tree_Snapshot_Design_v1.md`

---

## 1. 전체 평가

문제 정의가 명확하고, immutability + content-addressing 기반 스냅샷 모델은 잘 설계되어 있음.
핵심 검토 포인트는 **SCODA 범용 메커니즘과 도메인 로직의 경계**를 어디에 둘 것인가.

---

## 2. 범용성 검토: Tree Opinion은 범용 패턴인가?

"계층 구조에 대한 복수의 의견 → 하나를 선택/합성 → 스냅샷으로 고정"이라는 패턴은
taxonomy에만 해당하는 것이 아님:

| 도메인 | 예시 |
|--------|------|
| 생물 분류 | 복수의 분류 의견 중 하나를 채택 |
| 조직도 | 여러 조직 개편안 중 하나를 확정 |
| 분류 체계 | 상품 카테고리 구조의 버전별 변경 |
| 지질 시대 | ICS 차트의 시대별 개정 이력 |

따라서 Tree Snapshot의 **핵심 메커니즘** (스냅샷 저장, 해시 기반 UID, 규칙+오버라이드 구조)은
SCODA 범용 기능으로 설계할 여지가 있음.

### 범용 레이어 (SCODA Engine에 적합)

- 스냅샷 JSON 저장/조회/해시 생성
- content-addressed UID 체계 (`scoda:view:<package>:<hash>`)
- 범용 규칙/오버라이드 스키마 (tree node 재배치, 노드 상태 변경)
- 스냅샷 기반 tree resolve 프레임워크

### 도메인 레이어 (Trilobase에 적합)

- `opinion`, `assertion` 같은 도메인 테이블 정의
- `prefer_opinion`, `treat_as_valid` 같은 도메인 규칙 타입
- `synonym_policy`, `rank_policy` 같은 도메인 정책
- 도메인별 충돌 감지 로직 (동일 taxon에 복수 parent 등)

**제안:** 2-layer 설계.
SCODA Engine이 범용 snapshot framework를 제공하고,
Trilobase가 도메인 규칙/정책을 플러그인으로 등록하는 구조.

---

## 3. 기존 아키텍처와의 관계

### 3.1 Overlay DB와의 관계

현재 SCODA의 overlay DB는 user annotations 용도.
스냅샷의 overrides는 overlay와 성격이 다름:

| | Overlay DB | Snapshot Override |
|---|-----------|-------------------|
| 목적 | 사용자 메모/수정 | 구조적 의사결정 |
| 수명 | 가변 (CRUD) | 불변 (immutable) |
| 범위 | 개별 엔티티 | 전체 tree 구조 |

→ 별도 저장소가 적절. 스냅샷은 canonical DB 내 테이블 또는 별도 JSON 파일.

### 3.2 Manifest와의 관계

현재 manifest의 `hierarchy` 뷰는 단일 source_query로 tree를 구성.
스냅샷 시스템이 도입되면 source_query 대신 "resolved tree" 결과를 사용해야 함.
manifest 스펙에 `source_snapshot` 같은 필드 확장이 필요할 수 있음.

---

## 4. 문서 품질 이슈

### 포맷 아티팩트

Section 3.3에 pandoc 변환 잔여물:
```
```{=html}
<!-- -->
```

Section 9 리스트 포맷 깨짐:
> Server responsibilities (future): - Store immutable snapshot JSON - Provide retrieval by hash...

→ 마크다운 정리 필요.

### Section 5 구체성 부족

Internal Data Model에 테이블명만 나열되어 있고 스키마(컬럼, 관계)가 없음.
Phase 1 착수 전에 구체 스키마 정의 필요.

---

## 5. 구현 로드맵 의견

### Phase 1 스코프 축소 권장

현재 Phase 1: opinion 기반 rule + override + UID + export/import → 여전히 큼.

**제안 — Phase 0 (Proof of Concept):**
1. 수동으로 작성한 snapshot JSON 저장/로드
2. SHA-256 content-addressed UID 생성
3. 스냅샷 기준으로 tree 표시 (단순 parent override만)

**Phase 1:**
4. Rule engine (prefer_opinion 등)
5. Conflict Inspector UI

**Phase 2:**
6. Conditional priorities, policy 시스템
7. Snapshot diff 비교
8. Server 연동

---

## 6. 요약

| 항목 | 평가 |
|------|------|
| 문제 정의 | 명확하고 타당 |
| 개념 모델 (immutability, content-addressing) | 좋음 |
| 범용성 | Tree opinion 패턴은 SCODA 범용으로 설계 가능 |
| 설계 방향 | 2-layer (범용 framework + 도메인 plugin) 권장 |
| 기존 아키텍처 연동 | overlay/manifest와의 관계 정의 필요 |
| Phase 1 스코프 | 축소 권장 (Phase 0 POC 선행) |
| 문서 포맷 | pandoc 아티팩트 정리 필요 |

---

## 7. 후속 검토 필요 항목

본 검토는 구조적/방향성 수준의 의견이며, 설계를 본격 진행하기 전에
아래 항목들에 대한 심층 검토가 필요함.

### 7.1 Snapshot JSON 스키마 심층 검토

- **rules 필드 확장성**: `prefer_opinion` 외에 어떤 규칙 타입이 필요한가?
  범용 레이어에서 지원할 규칙 타입과 도메인 전용 타입의 경계 정의
- **overrides 필드 의미론**: `set_parent`, `treat_as_valid` 외에 어떤 오버라이드가 가능한가?
  범용 오버라이드 (노드 이동, 삭제, 속성 변경)와 도메인 오버라이드의 분리
- **options 필드 버전 호환성**: 정책이 추가/변경될 때 이전 스냅샷과의 호환성 보장 방법
- **스키마 버전 관리**: `schema: "scoda.view_snapshot.v1"` → v2 전환 시 마이그레이션 전략

### 7.2 Resolve 알고리즘 설계

- **우선순위 충돌 해결**: 동일 노드에 복수 규칙이 적용될 때 결정 로직
  (priority 숫자 비교만으로 충분한가? tie-breaking 정책은?)
- **Cycle detection**: override로 인한 순환 참조 감지 및 처리 방법
- **부분 resolve**: 규칙으로 해결 안 되는 노드의 처리
  (에러? 경고? 기본값 적용?)
- **성능**: 대규모 tree (수만 노드)에서의 resolve 성능 고려

### 7.3 2-Layer API 경계 설계

- **범용 프레임워크가 도메인 플러그인에 노출할 인터페이스 정의**
  (규칙 타입 등록, 충돌 해결 콜백, 정책 핸들러 등)
- **플러그인 디스커버리**: 도메인 규칙을 어떻게 등록하는가?
  (.scoda 패키지 내 설정 파일? manifest 확장? Python entry point?)
- **범용 규칙의 최소 집합**: 도메인 플러그인 없이도 동작하는 기본 규칙은 무엇인가?
  (예: `set_parent`, `remove_node`, `set_attribute` 정도?)

### 7.4 기존 시스템 통합 시나리오

- **manifest 확장 구체안**: `source_snapshot` 필드가 실제로 어떻게 동작하는가?
  hierarchy 뷰에서 source_query와 source_snapshot이 공존할 때의 우선순위
- **API 엔드포인트 설계**: 스냅샷 CRUD, resolve 결과 조회 등의 REST API
- **generic viewer 변경 범위**: 스냅샷 선택 UI, resolve된 tree 표시 등
  기존 app.js에 어느 정도 변경이 필요한가?
- **MCP 도구 확장**: 스냅샷 관련 MCP 도구 (생성, 조회, 비교) 설계

### 7.5 저장소/영속성 설계

- **스냅샷 JSON의 물리적 저장 위치**: canonical DB 내 테이블 vs 별도 JSON 파일 vs overlay DB
- **resolved tree 캐싱 전략**: 매번 resolve vs 결과 캐싱?
  캐시 무효화 조건은? (패키지 버전 변경 시 자동 무효화?)
- **스냅샷 간 공유/참조**: 다른 패키지의 스냅샷을 참조할 수 있는가?
  (의존 패키지의 tree 구조를 가져오는 경우)

### 7.6 사용자 워크플로우 구체화

- **View Builder UI 상세 설계**: 규칙 추가/제거, 우선순위 조정 인터페이스
- **Conflict Inspector 상호작용**: 충돌 목록 표시 → 사용자 선택 → override 자동 생성 흐름
- **스냅샷 비교 UI**: 두 스냅샷 간 차이를 어떻게 시각화할 것인가?
  (tree diff? 노드별 변경 목록?)
