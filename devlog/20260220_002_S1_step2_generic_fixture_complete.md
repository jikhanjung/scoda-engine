# S-1 Step 2: Generic Fixture 완전 전환 (dependency 포함)

**작성일:** 2026-02-20

---

## 목표

Step 1에서 전환하지 못한 나머지 7개 테스트 클래스 + straggler 3개를 generic fixture로 전환하고, `release.py`를 범용화하여 old trilobase fixture를 완전히 제거한다.

## 작업 내용

### Part A: release.py 범용화

`scripts/release.py`에서 hardcoded trilobase 참조를 모두 제거:

| 함수 | 변경 내용 |
|------|----------|
| `get_statistics()` | taxonomic_ranks/synonyms/bibliography 하드코딩 -> SCODA 메타 테이블 제외 auto-discover |
| `build_metadata_json()` | default `'trilobase'` -> `'unknown'` |
| `generate_readme()` | artifact_id/name 파라미터 추가, stats dict iteration |
| `create_release()` | DB에서 artifact_id 읽어서 directory/file naming |
| `main()` | DB에서 artifact_id 읽어서 dry-run 출력 |

신규 함수: `get_artifact_id()`, `get_artifact_name()`

### Part B: generic_db UID 칼럼 추가

- `categories`, `items` 테이블에 `uid, uid_method, uid_confidence, same_as_uid` + UNIQUE index 추가
- `references` 테이블 신규 추가 (bibliography 대체):
  - Newton fp_v1 (medium), Einstein doi (high), SEE Darwin cross_ref (low)
- UID 포맷: `scoda:cat:<level>:<name>`, `scoda:item:name:<name>`, `scoda:ref:<method>:<value>`

### Part C: generic_dep_db fixture 신규

paleocore DB 대체. `dep` alias로 ATTACH.

| 테이블 | 역할 | 데이터 |
|--------|------|--------|
| `regions` | countries 대체 | Europe(EU), Asia(AS) |
| `locations` | geographic_regions 대체 | 2 region + 2 subregion |
| `time_periods` | temporal_ranges 대체 | ERA-A, ERA-B |
| `time_mapping` | temporal_ics_mapping 대체 | 2건 |
| `entries` | formations 대체 | Alpha(fp_v1), Beta(fp_v1), Gamma(lexicon) |

artifact_id: `dep-data`, SCODA 코어 테이블 포함.

### Part D: 지원 fixture 3개

1. `generic_dep_client` — generic_db + generic_dep_db, `extra_dbs={'dep': dep_path}`
2. `generic_mcp_tools_data` — items/category_tree/item_detail 참조 (3 tools)
3. `generic_scoda_with_mcp_tools` — 3-tuple 반환 (scoda_path, canonical, overlay)

### Part E: 테스트 클래스 전환 (7 + 3)

| 클래스 | 테스트 수 | 주요 변경 |
|--------|----------|----------|
| TestRelease | 12 | stats assertion 전면 재작성 (auto-discover 기반) |
| TestPackageRegistry | 8 | trilobase->sample-data, paleocore->dep-data, pc->dep |
| TestActivePackage | 2 | 테이블/이름 변경 |
| TestDynamicMcpTools | 22 | SQL/쿼리명/composite view 전면 변경 |
| TestUIDSchema | 12 | categories+items UID, dep tables UID 검증 |
| TestUIDPhaseB | 4 | regions<->locations 일관성 검증 |
| TestUIDPhaseC | 14 | references/entries UID 검증 |
| Stragglers | 3 | client->generic_client, test_db->generic_db |

### Part F: Old fixture 삭제

- `test_db` fixture (~1100줄) 삭제
- `client` fixture 삭제
- `mcp_tools_data` fixture 삭제
- `scoda_with_mcp_tools` fixture 삭제
- conftest.py 모듈 docstring 업데이트
- 총 ~1183줄 삭제

## 결과

```
190 passed (189 test_runtime + 1 test_mcp_basic)
```

- conftest.py: 1975줄 -> 792줄 (60% 축소)
- test_runtime.py: 전체 23개 테스트 클래스가 generic fixture 사용
- scripts/release.py: 도메인 독립적 — 어떤 SCODA artifact에서도 동작
- 5 test_mcp.py 실패: 기존 문제 (subprocess MCP 테스트에 .scoda 필요)

## S-1 완료 상태

Step 1 + Step 2 완료로 S-1 Generic Fixture 전환 작업이 완료되었다:
- 모든 테스트가 도메인 독립적 generic fixture 사용
- trilobase 도메인 데이터 및 paleocore 참조 완전 제거
- production code (release.py)도 범용화 완료
