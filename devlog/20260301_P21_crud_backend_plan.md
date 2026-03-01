# P21: Assertion DB 편집 백엔드 구현 계획

**작성일:** 2026-03-01

---

## Context

현재 scoda-engine은 읽기 전용 API만 제공. Assertion DB(taxon, assertion, reference)를 웹에서 CRUD하고, `.scoda` 패키지로 빌드할 수 있는 편집 기능이 필요하다. scoda-engine에 manifest-driven CRUD 프레임워크를 추가하고, trilobase assertion DB에 적용한다.

**실행 방식:**
```bash
# 뷰어 모드 (기존 — .scoda 패키지, 읽기 전용)
python -m scoda_engine.serve --scoda-path dist/trilobase.scoda

# 편집 모드 (신규 — raw .db 파일 직접 편집)
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.2.db --mode admin
```

- `--scoda-path`: .scoda 패키지 열기 (ZIP 추출, 읽기 전용). `--mode admin` 불가.
- `--db-path`: raw .db 파일 직접 열기. `--mode admin` 허용.
- ScodaDesktop GUI에는 admin 모드를 노출하지 않음 (CLI 전용).

---

## Phase 0: scoda-engine CRUD 프레임워크

### Step 0.1: Admin/Viewer 모드 인프라

**수정 파일:**
- `scoda_engine/serve.py` — `--db-path`, `--mode admin|viewer` CLI 인자
- `scoda_engine/app.py` — 전역 `SCODA_MODE`, `/api/manifest` 응답에 `mode` 포함

```python
# serve.py: CLI 인자 추가
parser.add_argument('--db-path', type=str, default=None,
                    help='Raw .db file path for direct editing')
parser.add_argument('--mode', default='viewer', choices=['viewer', 'admin'])
# --mode admin은 --db-path와 함께만 사용 가능 (--scoda-path와 불가)

# app.py: 모드 전역 변수
SCODA_MODE = os.environ.get('SCODA_MODE', 'viewer')

# /api/manifest 응답에 mode 추가
return {**manifest_data, "mode": SCODA_MODE}
```

write 엔드포인트에 `_require_admin()` 가드 → viewer 모드에서 403.

### Step 0.2: Entity Schema 파서

**새 파일**: `scoda_engine/entity_schema.py`

manifest `editable_entities`를 파싱하여 `EntitySchema` 객체로 변환.

```python
@dataclass
class FieldDef:
    name: str
    type: str            # 'text', 'integer', 'boolean', 'json', 'real'
    required: bool = False
    enum: list | None = None
    fk: str | None = None       # 'table.column'
    default: Any = None
    label: str | None = None

@dataclass
class EntitySchema:
    name: str
    table: str
    pk: str
    operations: set          # {'create', 'read', 'update', 'delete'}
    fields: dict[str, FieldDef]
    constraints: list = field(default_factory=list)
    hooks: list = field(default_factory=list)
    list_query: str | None = None
    detail_query: str | None = None

def parse_editable_entities(manifest: dict) -> dict[str, EntitySchema]
def validate_input(schema: EntitySchema, data: dict, operation: str) -> list[str]
```

### Step 0.3: CRUD 엔진

**새 파일**: `scoda_engine/crud_engine.py`

EntitySchema 기반 제네릭 CRUD.

```python
class CrudEngine:
    def __init__(self, conn, schema: EntitySchema)
    def create(self, data: dict) -> dict          # INSERT + fetch back
    def read(self, pk_value) -> dict | None       # SELECT by PK
    def update(self, pk_value, data: dict) -> dict | None  # partial UPDATE
    def delete(self, pk_value) -> bool             # DELETE
    def list(self, filters=None, page=1, per_page=50, search=None) -> dict
    def check_constraints(self, data, pk_value=None) -> list[str]
    def execute_hooks(self, data, operation) -> None
```

- 필드명은 schema 화이트리스트 검증
- 값은 파라미터화 쿼리
- FK 존재 확인 (SELECT)
- unique_where 제약 검사
- 훅: 트랜잭션 내 실행, 조건부 트리거 (`trigger_when`)

### Step 0.4: REST API 엔드포인트

**수정 파일**: `scoda_engine/app.py`

```
GET    /api/entities                          # 엔티티 타입 + 스키마 (양쪽 모드)
GET    /api/entities/{type}                   # 목록 (pagination, search)
GET    /api/entities/{type}/{pk}              # 단건 조회
POST   /api/entities/{type}                   # 생성 (admin only) → 201
PATCH  /api/entities/{type}/{pk}              # 부분 수정 (admin only)
DELETE /api/entities/{type}/{pk}              # 삭제 (admin only)
POST   /api/entities/{type}/hooks/{name}      # 수동 훅 (admin only)
GET    /api/search/{type}?q=...               # FK autocomplete 검색
```

`editable_entities`가 manifest에 없으면 → 모든 entity 엔드포인트 404.

### Step 0.5: 편집 UI (프론트엔드)

**수정 파일:**
- `scoda_engine/static/js/app.js` — 편집 기능 추가
- `scoda_engine/templates/index.html` — 편집 모달 (필요 시)

**모드 감지:**
```javascript
let appMode = 'viewer';  // manifest 응답의 mode 필드에서 설정
```

**admin 모드에서 추가되는 UI:**

1. **Detail 모달에 Edit 버튼**
   - 기존 detail 모달 헤더에 Edit/Delete 버튼 (admin && editable_entities 있을 때)
   - Edit 클릭 → 필드가 폼으로 전환 (text→input, enum→select, boolean→checkbox)
   - Save → `PATCH /api/entities/{type}/{pk}`
   - Delete → 확인 다이얼로그 → `DELETE /api/entities/{type}/{pk}`

2. **테이블/목록에 Add 버튼**
   - linked_table, table 뷰에 "+" 버튼
   - 클릭 → 빈 폼 모달 → `POST /api/entities/{type}`

3. **FK 필드 autocomplete**
   - FK 필드에 검색 input
   - 입력 시 `GET /api/search/{fk_table}?q=...` 호출
   - 결과 드롭다운에서 선택 → ID 설정

4. **폼 자동 생성**
   - `/api/entities` 스키마 정보로 폼 필드 자동 렌더링
   - 필수 필드 표시, enum 드롭다운, 기본값 사전 입력

### Step 0.6: MCP 서버 확장

**수정 파일**: `scoda_engine/mcp_server.py`

admin 모드 + editable_entities 존재 시 빌트인 CRUD 도구 등록:
- `create_entity(entity_type, data)`
- `update_entity(entity_type, id, data)`
- `delete_entity(entity_type, id)`
- `list_entity_types()`

### Step 0.7: Manifest 검증

**수정 파일**: `core/scoda_engine_core/validate_manifest.py`

`editable_entities` 검증 규칙 추가:
- 필수: `table`, `pk`
- `fields` 내 타입 유효성
- `list_query`/`detail_query`가 ui_queries에 있는지
- 훅 SQL 형식

### Step 0.8: 테스트

**새 파일**: `tests/test_crud.py`

```python
# 제네릭 fixture (도메인 독립 — items/categories 테이블 사용)
def test_list_entity_types()       # GET /api/entities
def test_create_entity()           # POST → 201
def test_read_entity()             # GET by PK
def test_update_entity()           # PATCH
def test_delete_entity()           # DELETE
def test_list_with_pagination()    # page, per_page
def test_required_field_missing()  # → 400
def test_enum_validation()         # → 400
def test_fk_validation()           # → 400
def test_unique_constraint()       # → 409
def test_post_mutation_hook()      # 훅 실행 확인
def test_viewer_mode_blocks_write()# → 403
def test_no_editable_entities()    # → 404
def test_search_endpoint()         # FK autocomplete
```

**수정 파일**: `tests/conftest.py` — `crud_db` fixture (editable_entities 포함 manifest)

---

## Phase 1: Trilobase Assertion DB 적용

### Step 1.1: Assertion DB manifest에 editable_entities 추가

**수정 파일**: `scripts/create_assertion_db.py` (trilobase 레포)

`_build_manifest()` 함수의 manifest_json에 `editable_entities` 섹션 추가:

| 엔티티 | 테이블 | 연산 | 훅 |
|--------|--------|------|-----|
| taxon | taxon | CRUD | - |
| assertion | assertion | CRUD | PLACED_IN 시 edge cache 재생성 |
| reference | reference | CRU | - |
| classification_profile | classification_profile | CRUD | - |

Edge cache 재생성 훅 (manifest에 선언):
```json
{
  "name": "rebuild_edge_cache",
  "trigger_when": {"predicate": "PLACED_IN"},
  "steps": [
    {"sql": "DELETE FROM classification_edge_cache WHERE profile_id = 1"},
    {"sql": "INSERT INTO classification_edge_cache (profile_id, child_id, parent_id) SELECT 1, subject_taxon_id, object_taxon_id FROM assertion WHERE predicate = 'PLACED_IN' AND is_accepted = 1"}
  ]
}
```

### Step 1.2: Assertion DB 재빌드 + 테스트

```bash
python scripts/create_assertion_db.py  # manifest 포함 DB 재생성
pytest tests/ -v                       # 기존 112 테스트 + 새 검증
```

**수정 파일**: `tests/test_trilobase.py`
- assertion DB manifest에 editable_entities 존재 확인
- 스키마 검증 (필수 필드, 타입, FK 선언 정합성)

---

## Manifest `editable_entities` 스키마 예시

```json
{
  "editable_entities": {
    "assertion": {
      "table": "assertion",
      "pk": "id",
      "operations": ["create", "read", "update", "delete"],
      "fields": {
        "subject_taxon_id": {"type": "integer", "required": true, "fk": "taxon.id", "label": "Subject Taxon"},
        "predicate": {"type": "text", "required": true, "enum": ["PLACED_IN", "SYNONYM_OF", "SPELLING_OF"], "label": "Predicate"},
        "object_taxon_id": {"type": "integer", "fk": "taxon.id", "label": "Object Taxon"},
        "reference_id": {"type": "integer", "fk": "reference.id", "label": "Reference"},
        "assertion_status": {"type": "text", "default": "asserted", "enum": ["asserted", "incertae_sedis", "questionable", "indet"]},
        "is_accepted": {"type": "boolean", "default": 0},
        "notes": {"type": "text"}
      },
      "constraints": [
        {"type": "unique_where", "columns": ["subject_taxon_id", "predicate"], "where": "is_accepted = 1", "error_message": "Only one accepted assertion per subject+predicate"}
      ],
      "post_mutation_hooks": [
        {"name": "rebuild_edge_cache", "trigger_when": {"predicate": "PLACED_IN"}, "steps": [{"sql": "..."}, {"sql": "..."}]}
      ],
      "list_query": "assertion_list",
      "detail_query": "taxon_assertions"
    }
  }
}
```

---

## 실행 순서

```
Phase 0 (scoda-engine):
  0.1 모드 인프라 (serve.py, app.py) ──────────────┐
  0.2 entity_schema.py ──┐                         │
                         ├→ 0.4 app.py REST ────────┤
  0.3 crud_engine.py ────┤                         ├→ 0.8 tests
                         ├→ 0.5 app.js 편집 UI ─────┤
                         ├→ 0.6 mcp_server.py ──────┤
                         └→ 0.7 validate_manifest ──┘

Phase 1 (trilobase):
  1.1 assertion DB manifest
  1.2 테스트
```

## 검증 방법

```bash
# 1. scoda-engine CRUD 테스트
cd /mnt/d/projects/scoda-engine
pytest tests/test_crud.py -v
pytest tests/ -v  # 기존 276+ 깨지지 않음

# 2. trilobase 테스트
cd /mnt/d/projects/trilobase
pytest tests/ -v  # 기존 112 + 새 테스트

# 3. 수동 검증 — admin 모드로 편집 서버 실행
cd /mnt/d/projects/trilobase
python -m scoda_engine.serve --db-path db/trilobase-assertion-0.1.2.db --mode admin --port 8090
# 브라우저에서 http://localhost:8090 접속
# → detail 모달에서 Edit/Delete, 목록에서 Add 확인
```

## 향후 확장

- ScodaDesktop GUI에 admin 모드 드롭다운 추가
- Overlay 기반 편집 (.scoda 불변 유지)
- `.scoda` 빌드 버튼 (편집 완료 후 패키징)
- Tree Snapshot 통합
