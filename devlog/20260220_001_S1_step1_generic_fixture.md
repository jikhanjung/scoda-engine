# S-1 Step 1: Generic Fixture 전환 (dependency 없는 패키지)

**작성일:** 2026-02-20

---

## 목표

테스트 fixture에서 trilobase 도메인 데이터를 제거하고, dependency(외부 DB) 없이 동작하는 범용 fixture를 먼저 구축한다.

## 배경

기존 `test_db` fixture는:
- `taxonomic_ranks`, `synonyms`, `bibliography` 등 삼엽충 분류 테이블 사용
- `paleocore.db`를 `pc.*` alias로 ATTACH하는 3-DB 구조 (canonical + overlay + dependency)
- 30개 named query, 13-view manifest

SCODA Engine은 도메인 무관 범용 런타임이므로 테스트도 도메인 독립적이어야 한다.

## 작업 내용

### 1. Generic Fixture 추가 (`tests/conftest.py`)

**`generic_db`** — dependency 없는 독립 패키지:

| 테이블 | 역할 |
|--------|------|
| `categories` | 3단계 계층 (root → group → subgroup) |
| `items` | 리프 레코드 5건 |
| `item_relations` | 아이템 간 관계 1건 |
| `tags` | 아이템 태그 4건 |
| + SCODA 코어 | artifact_metadata, provenance, schema_descriptions, ui_display_intent, ui_queries, ui_manifest |

- Named queries: 11개 (all local, no cross-DB)
- Manifest views: 4개 (category_tree, items_table, item_detail, category_detail)
- Display intents: 2개

**`generic_client`** — `generic_db` 기반 TestClient (`_set_paths_for_testing` without `extra_dbs`)

### 2. 테스트 마이그레이션 (`tests/test_runtime.py`)

16개 클래스를 `generic_client` / `generic_db`로 전환:

**단순 fixture 교체 (assertion 변경 없음):**
- TestCORS, TestMCPMount, TestOpenAPIDocs, TestIndex
- TestGenericViewer, TestGenericViewerFallback

**fixture + assertion 변경:**
- TestApiProvenance — citation/year 값 변경
- TestApiDisplayIntent — entity: genera→items, query: taxonomy_tree→category_tree
- TestApiQueries — query count: 30→11
- TestApiQueryExecute — query name/row count 변경
- TestApiManifest — view 이름/개수 변경 (13→4)
- TestAnnotations — entity_type/entity_id 변경
- TestGenericDetailEndpoint — query name 변경

**Composite/Package 전환:**
- TestCompositeDetail — sub_query 구조 전면 재작성 (hierarchy, relations, tags, related_items)
- TestScodaPackage — 2-tuple unpack, table ref 변경
- TestScodaPackageSPA — 2-tuple unpack

### 3. 기존 fixture 유지 (Step 2 대상)

다음 클래스는 dependency DB 또는 도메인 전용 데이터가 필요하여 `test_db`/`client` 유지:

| 클래스 | 이유 |
|--------|------|
| TestRelease | `release.py`의 `get_statistics()`가 taxonomic_ranks 직접 참조 |
| TestPackageRegistry | `test_dependency_resolution_with_alias` 등 ATTACH 테스트 |
| TestDynamicMcpTools | `extra_dbs={'pc': ...}` 필요 |
| TestActivePackage | dependency 포함 패키지 설정 |
| TestUIDSchema, TestUIDPhaseB, TestUIDPhaseC | trilobase/paleocore UID 포맷 검증 |

## 결과

```
189 passed in 144.96s
```

- 전환된 테스트: ~120개 (16개 클래스)
- 기존 fixture 유지 테스트: ~69개 (7개 클래스)
- 실패: 0

## Generic Fixture 데이터 요약

```
categories:
  1: Science (root)
    2: Physics (group)
      4: Mechanics (subgroup)
    3: Biology (group)
      5: Ecology (subgroup)

items:
  1: Gravity     → Mechanics  (Newton, 1687, active)
  2: Relativity  → Physics    (Einstein, 1905, active)
  3: Evolution   → Biology    (Darwin, 1859, active)
  4: Photosynthesis → Ecology (Priestley, 1771, active)
  5: Alchemy     → Physics    (Unknown, 800, inactive)

item_relations:
  Alchemy → superseded_by → Relativity

tags:
  Gravity: classical, fundamental
  Relativity: modern
  Evolution: foundational
```

## 다음 단계 (Step 2)

- dependency 있는 generic fixture 추가 (`refs` DB를 ATTACH)
- TestPackageRegistry, TestDynamicMcpTools, TestActivePackage 전환
- TestRelease: `release.py` 범용화 필요 (hardcoded trilobase 참조 제거)
- TestUID*: SCODA UID 메커니즘 테스트로 추상화 가능 여부 검토
- 전체 전환 완료 후 old trilobase fixture 삭제
