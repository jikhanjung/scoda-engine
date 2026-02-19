# SCODA Desktop REST API Reference

**버전:** 2.0.0
**Base URL:** `http://localhost:8080`

---

## 목차

- [개요](#개요)
- [Core API](#core-api)
- [Query API](#query-api)
- [Composite Detail API](#composite-detail-api)
- [Metadata API](#metadata-api)
- [Annotations API](#annotations-api)
- [에러 코드](#에러-코드)
- [예제 코드](#예제-코드)

---

## 개요

SCODA Desktop REST API는 `.scoda` 패키지에 포함된 데이터에 대한 프로그래매틱 접근을 제공합니다. 모든 응답은 JSON 형식이며, HTTP 상태 코드로 성공/실패를 나타냅니다.

### 기본 원칙

- **도메인 무관(Domain-Agnostic)**: 모든 엔드포인트는 범용이며, 데이터 구조는 `.scoda` 패키지의 manifest와 named queries로 정의
- **Read-Only (Canonical DB)**: 패키지 데이터는 읽기 전용
- **Read/Write (Overlay DB)**: 사용자 주석만 쓰기 가능
- **CORS**: 모든 origin 허용 (외부 SPA 지원)

### 엔드포인트 요약

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/manifest` | GET | UI Manifest (뷰 정의) |
| `/api/provenance` | GET | 데이터 출처 |
| `/api/display-intent` | GET | Display Intent 힌트 |
| `/api/queries` | GET | Named Query 목록 |
| `/api/queries/<name>/execute` | GET | Named Query 실행 |
| `/api/detail/<query_name>` | GET | 단일 레코드 조회 (첫 행) |
| `/api/composite/<view_name>` | GET | 복합 Detail 조회 |
| `/api/annotations/<type>/<id>` | GET | 주석 조회 |
| `/api/annotations` | POST | 주석 생성 |
| `/api/annotations/<id>` | DELETE | 주석 삭제 |

---

## Core API

### GET /api/manifest

UI Manifest (선언적 뷰 정의)를 조회합니다. 프론트엔드가 화면을 구성하는 데 사용합니다.

**Parameters:** 없음

**Response:**
```json
{
  "name": "default",
  "description": "Default UI manifest",
  "manifest": {
    "default_view": "taxonomy_tree",
    "views": [
      {
        "id": "taxonomy_tree",
        "type": "tree",
        "title": "Taxonomy Tree",
        "query": "taxonomy_tree",
        "tree_options": { ... }
      },
      {
        "id": "genera_table",
        "type": "table",
        "title": "All Genera",
        "query": "genera_list",
        "columns": [ ... ],
        "on_row_click": { "detail_view": "genus_detail", "id_column": "id" }
      },
      {
        "id": "genus_detail",
        "type": "detail",
        "title_template": "{name}",
        "source_query": "genus_detail_main",
        "source_param": "id",
        "sections": [ ... ],
        "sub_queries": { ... }
      }
    ]
  },
  "created_at": "2026-02-05 10:00:00"
}
```

**View Types:**
- `tree`: 계층 트리 뷰 (tree_options 포함)
- `table`: 테이블 뷰 (columns, on_row_click 포함)
- `chart`: 차트 뷰 (chart_options 포함)
- `detail`: 상세 뷰 (sections, source_query, sub_queries 포함)

---

### GET /api/provenance

데이터 출처 정보를 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "source_type": "primary",
    "citation": "Jell, P.A. & Adrain, J.M. 2002",
    "description": "Available Generic Names for Trilobites",
    "year": 2002,
    "url": null
  }
]
```

---

### GET /api/display-intent

SCODA Display Intent 힌트를 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "entity": "genera",
    "default_view": "tree",
    "description": "Hierarchical taxonomy browser",
    "source_query": "taxonomy_tree",
    "priority": 1
  }
]
```

---

## Query API

### GET /api/queries

사용 가능한 Named Query 목록을 조회합니다.

**Parameters:** 없음

**Response:**
```json
[
  {
    "id": 1,
    "name": "taxonomy_tree",
    "description": "Get full taxonomy tree from Class to Family",
    "params": "{}",
    "created_at": "2026-02-05 10:00:00"
  },
  {
    "id": 2,
    "name": "family_genera",
    "description": "Get all genera in a family",
    "params": "{\"family_id\": null}",
    "created_at": "2026-02-05 10:00:00"
  }
]
```

---

### GET /api/queries/:name/execute

Named Query를 실행합니다.

**Parameters:**
- `name` (path, required): Query 이름
- Query별 파라미터 (query string)

**예시:**
```
GET /api/queries/family_genera/execute?family_id=42
```

**Response:**
```json
{
  "query": "family_genera",
  "columns": ["id", "name", "author", "year"],
  "row_count": 89,
  "rows": [
    {"id": 100, "name": "Paradoxides", "author": "BRONGNIART", "year": 1822}
  ]
}
```

**Error:**
- `404`: Query not found
- `400`: SQL execution error

---

### GET /api/detail/:query_name

Named Query를 실행하고 **첫 번째 행**을 flat JSON으로 반환합니다. 단일 레코드 조회에 적합합니다.

**Parameters:**
- `query_name` (path, required): Query 이름
- Query별 파라미터 (query string)

**예시:**
```
GET /api/detail/genus_detail_main?id=100
```

**Response:**
```json
{
  "id": 100,
  "name": "Paradoxides",
  "author": "BRONGNIART",
  "year": 1822,
  "rank": "Genus",
  "is_valid": 1
}
```

**Error:**
- `404`: Query not found or no results

---

## Composite Detail API

### GET /api/composite/:view_name

Manifest에 정의된 detail view를 기반으로 **복합 쿼리**를 실행합니다. 메인 쿼리(source_query)와 하위 쿼리(sub_queries)를 병합하여 반환합니다.

**Parameters:**
- `view_name` (path, required): Manifest detail view의 ID
- `id` (query, required): Entity ID

**예시:**
```
GET /api/composite/genus_detail?id=100
```

**Response:**
```json
{
  "id": 100,
  "name": "Paradoxides",
  "author": "BRONGNIART",
  "year": 1822,
  "rank": "Genus",
  "is_valid": 1,
  "family_name": "Paradoxididae",
  "raw_entry": "Paradoxides BRONGNIART, 1822...",
  "synonyms": [
    {"junior_name": "Paradoxus", "synonym_type": "j.o.s.", "fide": "WHITTINGTON, 1997"}
  ],
  "formations": [
    {"name": "Jince Formation", "country": "Czech Republic"}
  ],
  "locations": [
    {"country": "Czech Republic", "region": "Bohemia"}
  ],
  "hierarchy": [
    {"id": 1, "name": "Trilobita", "rank": "Class"}
  ]
}
```

**동작 원리:**
1. Manifest에서 `view_name`에 해당하는 detail view를 찾음
2. `source_query`를 `id` 파라미터로 실행 (메인 데이터)
3. `sub_queries`를 순차 실행하여 결과를 메인 데이터에 병합
4. Sub-query 파라미터는 URL(`"id"`) 또는 메인 결과 필드(`"result.field_name"`)에서 가져옴

**Error:**
- `400`: `id` 파라미터 누락
- `404`: View not found, view가 detail 타입이 아님, source_query 없음, entity 없음

---

## Metadata API

메타데이터는 `/api/manifest` 응답에 포함됩니다. 별도의 `/api/metadata` 엔드포인트는 없습니다.

Manifest 응답의 최상위 필드(`name`, `description`, `created_at`)가 패키지 메타데이터 역할을 합니다. 상세 메타데이터는 MCP `get_metadata` 도구를 통해 조회할 수 있습니다.

---

## Annotations API

### GET /api/annotations/:entity_type/:entity_id

특정 Entity의 사용자 주석을 조회합니다.

**Parameters:**
- `entity_type` (path, required): `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `entity_id` (path, required): taxonomic_ranks.id

**Response:**
```json
[
  {
    "id": 1,
    "entity_type": "genus",
    "entity_id": 100,
    "entity_name": "Paradoxides",
    "annotation_type": "note",
    "content": "Check formation data for accuracy",
    "author": "researcher_1",
    "created_at": "2026-02-09 10:00:00"
  }
]
```

**Annotation Types:**
- `note`: 일반 메모
- `correction`: 수정 제안
- `alternative`: 대안 해석
- `link`: 외부 리소스 링크

---

### POST /api/annotations

새로운 주석을 생성합니다.

**Request Body:**
```json
{
  "entity_type": "genus",
  "entity_id": 100,
  "annotation_type": "note",
  "content": "Check formation data for accuracy",
  "author": "researcher_1"
}
```

**Required Fields:** `entity_type`, `entity_id`, `annotation_type`, `content`
**Optional Fields:** `author`

**Response:** 생성된 annotation 객체 (위 GET 응답과 동일 구조)

**Error:**
- `400`: Invalid entity_type or annotation_type
- `400`: Missing required field

---

### DELETE /api/annotations/:annotation_id

주석을 삭제합니다.

**Parameters:**
- `annotation_id` (path, required): user_annotations.id

**Response:**
```json
{
  "message": "Annotation deleted successfully"
}
```

**Error:**
- `404`: Annotation not found

---

## 에러 코드

| 코드 | 의미 | 설명 |
|-----|------|------|
| 200 | OK | 요청 성공 |
| 400 | Bad Request | 잘못된 요청 파라미터 |
| 404 | Not Found | 리소스를 찾을 수 없음 |
| 500 | Internal Server Error | 서버 내부 오류 |

**에러 응답 형식:**
```json
{
  "error": "Error message describing what went wrong"
}
```

---

## 예제 코드

### Python (requests)

```python
import requests

BASE = 'http://localhost:8080'

# Get manifest (뷰 정의 + 메타데이터)
manifest = requests.get(f'{BASE}/api/manifest').json()
print(f"Package: {manifest['name']}")

# Execute named query
result = requests.get(f'{BASE}/api/queries/genera_list/execute').json()
print(f"Found {result['row_count']} genera")

# Get composite detail (manifest-driven)
detail = requests.get(f'{BASE}/api/composite/genus_detail', params={'id': 100}).json()
print(f"{detail['name']} {detail['author']}, {detail['year']}")

# Create annotation
annotation = {
    "entity_type": "genus",
    "entity_id": 100,
    "annotation_type": "note",
    "content": "Interesting specimen from Jince Formation"
}
result = requests.post(f'{BASE}/api/annotations', json=annotation).json()
```

### JavaScript (fetch)

```javascript
const BASE = 'http://localhost:8080';

// Get manifest
const manifest = await (await fetch(`${BASE}/api/manifest`)).json();

// Execute named query
const result = await (await fetch(
  `${BASE}/api/queries/family_genera/execute?family_id=42`
)).json();

// Get composite detail
const detail = await (await fetch(
  `${BASE}/api/composite/genus_detail?id=100`
)).json();

// Create annotation
const annotation = await (await fetch(`${BASE}/api/annotations`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    entity_type: 'genus',
    entity_id: 100,
    annotation_type: 'note',
    content: 'Check this later'
  })
})).json();
```

### cURL

```bash
# Get manifest
curl http://localhost:8080/api/manifest

# Execute named query
curl 'http://localhost:8080/api/queries/genera_list/execute'

# Composite detail
curl 'http://localhost:8080/api/composite/genus_detail?id=100'

# Get provenance
curl http://localhost:8080/api/provenance

# Create annotation
curl -X POST http://localhost:8080/api/annotations \
  -H "Content-Type: application/json" \
  -d '{
    "entity_type": "genus",
    "entity_id": 100,
    "annotation_type": "note",
    "content": "Interesting specimen"
  }'

# Delete annotation
curl -X DELETE http://localhost:8080/api/annotations/1
```

---

## 주의사항

### SCODA 원칙

- **Canonical Data는 불변**: 패키지 데이터는 읽기 전용
- **User Annotations만 수정 가능**: Overlay DB에만 쓰기 허용
- **Manifest-Driven**: 뷰 구조, 쿼리, detail 구성 모두 manifest/named queries로 정의

### 성능

- Named Query는 서버의 `ui_queries` 테이블에 사전 정의되어 즉시 실행
- Composite detail은 source_query + sub_queries를 순차 실행하므로 약간의 지연 가능
- 인덱스: name, rank, parent_id, is_valid 등에 인덱스 적용

---

## 버전 히스토리

- **v2.0.0** (2026-02-14): Domain-agnostic API (Phase 46 Step 3)
  - Legacy 도메인 엔드포인트 11개 제거
  - `/api/composite/<view_name>` 추가 (manifest-driven 복합 조회)
  - `/api/detail/<query_name>` 추가 (단일 레코드 조회)
  - 모든 도메인 로직은 `.scoda` 패키지 내부로 이동
- **v1.0.0** (2026-02-09): Initial API release
  - 14 API endpoints (domain-specific)
  - SCODA metadata support
  - User annotations (Overlay DB)

---

## 참고 문서

- [MCP Guide](MCP_GUIDE.md) - MCP 서버 사용 가이드
- [SCODA Concept](SCODA_CONCEPT.md) - SCODA 개념 설명
- [HANDOFF](HANDOFF.md) - 프로젝트 현황

---

**Last Updated:** 2026-02-14
