# SCODA: Self-Contained Open Data Artifact

**A Specification for Portable, Declarative Scientific Data Packages**

**Version:** 1.0 Draft
**Date:** 2026-02-14
**Reference Implementation:** SCODA Desktop + Trilobase / PaleoCore packages

---

## Abstract

SCODA(Self-Contained Open Data Artifact)는 과학 데이터를 **불변의 버전화된 패키지**로 배포하기 위한 아키텍처이다. 기존의 서비스 기반 데이터 배포(API 서버, 클라우드 데이터베이스)와 달리, SCODA는 데이터·스키마·메타데이터·UI 정의를 하나의 자기완결적 파일로 묶어 배포한다.

SCODA는 세 가지 핵심 개념으로 구성된다:

1. **.scoda 패키지** — 데이터와 메타데이터를 담은 ZIP 기반 배포 단위
2. **SCODA Desktop** — .scoda 패키지를 열고 탐색하는 범용 뷰어
3. **Overlay DB** — 불변의 canonical 데이터 위에 사용자의 로컬 주석을 분리 저장하는 계층

이 문서는 SCODA의 설계 원칙, 패키지 포맷, 뷰어 아키텍처, 그리고 Trilobase(삼엽충 분류 데이터베이스)를 참조 구현으로 사용한 실증 내용을 기술한다.

---

## 목차

1. [설계 철학](#1-설계-철학)
2. [.scoda 패키지 포맷](#2-scoda-패키지-포맷)
3. [SCODA 메타데이터 계층](#3-scoda-메타데이터-계층)
4. [선언적 UI 매니페스트](#4-선언적-ui-매니페스트)
5. [SCODA Desktop 뷰어](#5-scoda-desktop-뷰어)
6. [Multi-DB 아키텍처](#6-multi-db-아키텍처)
7. [Overlay DB와 Local Annotations](#7-overlay-db와-local-annotations)
8. [MCP 서버 — LLM 통합 인터페이스](#8-mcp-서버--llm-통합-인터페이스)
9. [빌드 및 배포 파이프라인](#9-빌드-및-배포-파이프라인)
10. [Reference Implementation SPA](#10-reference-implementation-spa)
11. [참조 구현: Trilobase와 PaleoCore](#11-참조-구현-trilobase와-paleocore)
12. [부록: 파일 구조 및 API 목록](#12-부록-파일-구조-및-api-목록)

---

## 1. 설계 철학

### 1.1 "데이터베이스가 아니라 지식 객체"

과학 데이터는 서비스가 아니라 **출판물**이다. 논문이 출판 후 수정되지 않듯이, 데이터셋의 특정 버전도 불변해야 한다. SCODA는 이 원칙을 소프트웨어 아키텍처로 구현한다:

- **Trilobase는 연결하는 데이터베이스가 아니다. 여는 지식 객체다.**
- 각 릴리스는 **읽기 전용의 curated snapshot**이다.
- 데이터의 변경은 새 버전의 발행으로만 이루어진다.

### 1.2 핵심 원칙

| 원칙 | 설명 |
|------|------|
| **Immutability** | Canonical 데이터는 릴리스 후 변경 불가. 수정은 새 버전 발행으로만 이루어짐 |
| **Self-Containment** | 하나의 .scoda 파일 안에 데이터, 스키마, 메타데이터, UI 정의가 모두 포함됨 |
| **Declarative UI** | 뷰어가 데이터를 어떻게 표시할지를 데이터 자체가 선언함 (매니페스트) |
| **Separation of Concerns** | Canonical 데이터(불변) / Overlay 데이터(사용자 주석) / 인프라 데이터(공유) 분리 |
| **DB is Truth, Viewer is Narration** | DB가 유일한 진실의 원천. 뷰어(웹, LLM)는 서술자일 뿐 판단 주체가 아님 |
| **Provenance Always** | 모든 데이터에 출처가 명시됨. 근거 없는 주장은 허용하지 않음 |

### 1.3 SCODA가 의도적으로 하지 않는 것

SCODA는 **서비스**가 아니므로 다음을 의도적으로 배제한다:

- 실시간 협업 편집
- 서로 다른 해석의 자동 병합
- 중앙 집중식 라이브 API를 주된 인터페이스로 사용
- 과거 데이터의 암묵적 수정

---

## 2. .scoda 패키지 포맷

### 2.1 물리적 구조

.scoda 파일은 ZIP 압축 아카이브이며, 확장자만 `.scoda`로 변경한 것이다:

```
trilobase.scoda (ZIP archive)
├── manifest.json          # 패키지 메타데이터
├── data.db                # SQLite 데이터베이스
└── assets/                # 추가 리소스 (선택)
    └── spa/               # Reference SPA 파일 (선택)
        ├── index.html
        ├── app.js
        └── style.css
```

### 2.2 manifest.json

패키지의 정체성, 버전, 의존성, 무결성 정보를 담는 최상위 메타데이터 파일:

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "2.1.0",
  "title": "Trilobase - A catalogue of trilobite genera",
  "description": "A catalogue of trilobite genera",
  "created_at": "2026-02-14T00:00:00+00:00",
  "license": "CC-BY-4.0",
  "authors": ["Jell, P.A.", "Adrain, J.M."],
  "data_file": "data.db",
  "record_count": 17937,
  "data_checksum_sha256": "a1b2c3d4e5f6...",
  "dependencies": [
    {
      "name": "paleocore",
      "alias": "pc",
      "version": "0.3.0",
      "file": "paleocore.scoda",
      "description": "Shared paleontological infrastructure (geography, stratigraphy)"
    }
  ],
  "has_reference_spa": true,
  "reference_spa_path": "assets/spa/"
}
```

**주요 필드:**

| 필드 | 설명 |
|------|------|
| `format` / `format_version` | SCODA 포맷 식별자 및 버전 |
| `name` | 패키지의 고유 식별자 (파일명과 일치) |
| `version` | Semantic Versioning (MAJOR.MINOR.PATCH) |
| `data_file` | ZIP 내부의 SQLite DB 파일명 |
| `record_count` | 데이터 테이블 레코드 합계 (메타데이터 테이블 제외) |
| `data_checksum_sha256` | data.db의 SHA-256 체크섬 (무결성 검증용) |
| `dependencies` | 이 패키지가 런타임에 필요로 하는 다른 .scoda 패키지 목록 |
| `has_reference_spa` | Reference SPA 포함 여부 |

### 2.3 데이터 무결성

패키지 오픈 시 `data_checksum_sha256`으로 data.db의 무결성을 검증한다:

```python
pkg = ScodaPackage("trilobase.scoda")
assert pkg.verify_checksum()  # SHA-256 검증
```

### 2.4 패키지 생명주기

```
[Source DB] → create_scoda.py → [.scoda package]
                                      ↓
                              ScodaPackage.open()
                                      ↓
                              [temp dir에 data.db 추출]
                                      ↓
                              sqlite3.connect(temp/data.db)
                                      ↓
                              [ATTACH overlay + dependencies]
                                      ↓
                              [Flask/MCP 서비스 제공]
                                      ↓
                              ScodaPackage.close()
                                      ↓
                              [temp dir 자동 정리]
```

- .scoda 파일 내부의 data.db는 **직접 접근하지 않는다**
- 임시 디렉토리로 추출 후 SQLite로 열며, 프로세스 종료 시 자동 정리된다
- 원본 .scoda 파일은 항상 불변으로 유지된다

---

## 3. SCODA 메타데이터 계층

data.db 안에는 실제 데이터 테이블 외에 6개의 SCODA 메타데이터 테이블이 존재한다. 이 테이블들은 패키지의 정체성, 출처, 스키마 설명, UI 렌더링 힌트를 제공한다.

### 3.1 테이블 목록

| 테이블 | 역할 | 예시 레코드 수 |
|--------|------|---------------|
| `artifact_metadata` | 패키지 정체성 (key-value) | 7 |
| `provenance` | 데이터 출처 및 빌드 정보 | 3–5 |
| `schema_descriptions` | 모든 테이블/컬럼의 자연어 설명 | 80–94 |
| `ui_display_intent` | 엔티티별 기본 뷰 타입 힌트 | 4–6 |
| `ui_queries` | Named SQL 쿼리 (파라미터화) | 14–16 |
| `ui_manifest` | 선언적 뷰 정의 (JSON) | 1 |

### 3.2 artifact_metadata

패키지의 정체성을 key-value 쌍으로 저장:

```sql
CREATE TABLE artifact_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

| key | value (예시) |
|-----|-------------|
| `artifact_id` | `trilobase` |
| `name` | `Trilobase` |
| `version` | `2.1.0` |
| `schema_version` | `1.0` |
| `created_at` | `2026-02-14` |
| `description` | `A catalogue of trilobite genera` |
| `license` | `CC-BY-4.0` |

### 3.3 provenance

데이터의 학술적 출처와 빌드 파이프라인 정보:

```sql
CREATE TABLE provenance (
    id          INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,    -- 'reference' 또는 'build'
    citation    TEXT NOT NULL,
    description TEXT,
    year        INTEGER,
    url         TEXT
);
```

예시:

| id | source_type | citation | year |
|----|-------------|----------|------|
| 1 | reference | Jell, P.A. & Adrain, J.M. (2002). Available trilobite names... | 2002 |
| 2 | reference | Adrain, J.M. (2011). Class Trilobita... | 2011 |
| 3 | build | Trilobase build pipeline (2026). | 2026 |

### 3.4 schema_descriptions

모든 테이블과 컬럼에 대한 자연어 설명. LLM이 스키마를 이해하는 데 사용되며, 뷰어의 도움말에도 활용할 수 있다:

```sql
CREATE TABLE schema_descriptions (
    table_name  TEXT NOT NULL,
    column_name TEXT,          -- NULL이면 테이블 수준 설명
    description TEXT NOT NULL,
    PRIMARY KEY (table_name, column_name)
);
```

### 3.5 ui_display_intent

각 데이터 엔티티를 어떤 뷰 타입(tree, table, chart)으로 표시할지 힌트:

```sql
CREATE TABLE ui_display_intent (
    id           INTEGER PRIMARY KEY,
    entity       TEXT NOT NULL,      -- 'genera', 'countries', 'chronostratigraphy' 등
    default_view TEXT NOT NULL,      -- 'tree', 'table', 'chart'
    description  TEXT,
    source_query TEXT,               -- ui_queries.name 참조
    priority     INTEGER DEFAULT 0
);
```

### 3.6 ui_queries — Named SQL Queries

파라미터화된 SQL 쿼리를 DB 안에 저장. 뷰어는 쿼리 이름으로 실행한다:

```sql
CREATE TABLE ui_queries (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,   -- 'taxonomy_tree', 'family_genera', 'genera_list' 등
    description TEXT,
    sql         TEXT NOT NULL,          -- 실행할 SQL (파라미터: :param_name)
    params_json TEXT,                   -- 기본 파라미터 (JSON)
    created_at  TEXT NOT NULL
);
```

**핵심 설계 의도:** SQL은 DB 안에 있다. 뷰어는 SQL을 하드코딩할 필요 없이, 쿼리 이름과 파라미터만으로 데이터를 조회한다. 새로운 데이터 패키지를 열면 해당 패키지가 제공하는 쿼리 목록에 따라 뷰어가 자동으로 적응한다.

```python
# 뷰어 코드
result = execute_named_query("genera_list")
result = execute_named_query("family_genera", {"family_id": 42})
```

---

## 4. 선언적 UI 매니페스트

### 4.1 개요

`ui_manifest` 테이블은 단일 JSON 문서로 뷰어의 전체 UI 구조를 선언한다. 뷰어는 이 매니페스트를 읽고 탭, 테이블, 트리, 차트, 상세 모달을 **자동으로 생성**한다.

```sql
CREATE TABLE ui_manifest (
    name          TEXT PRIMARY KEY,    -- 'default'
    description   TEXT,
    manifest_json TEXT NOT NULL,       -- 전체 UI 정의 (JSON)
    created_at    TEXT NOT NULL
);
```

### 4.2 매니페스트 구조

```json
{
  "default_view": "taxonomy_tree",
  "views": {
    "taxonomy_tree": { ... },       // 탭 뷰: 트리
    "genera_table": { ... },        // 탭 뷰: 테이블
    "references_table": { ... },    // 탭 뷰: 테이블
    "chronostratigraphy_table": { ... },  // 탭 뷰: 차트
    "genus_detail": { ... },        // 상세 뷰: 모달
    "formation_detail": { ... },    // 상세 뷰: 모달
    ...
  }
}
```

### 4.3 뷰 타입

| type | 설명 | 예시 |
|------|------|------|
| `tree` | 계층형 트리 뷰 (expand/collapse) | 분류 체계 (Class→Order→...→Family) |
| `table` | 범용 테이블 뷰 (정렬/검색) | Genera, Countries, Formations, Bibliography |
| `chart` | 특수 차트 뷰 | ICS Chronostratigraphic Chart (계층형 색상 코딩) |
| `detail` | 상세 모달 뷰 (행 클릭 시) | Genus detail, Country detail, Formation detail |

### 4.4 Table View 정의 예시

```json
{
  "type": "table",
  "title": "All Genera",
  "description": "Complete list of trilobite genera",
  "source_query": "genera_list",
  "icon": "bi-list-ul",
  "columns": [
    {"key": "name", "label": "Genus", "sortable": true, "searchable": true, "format": "italic"},
    {"key": "author", "label": "Author", "sortable": true, "searchable": true},
    {"key": "year", "label": "Year", "sortable": true},
    {"key": "family", "label": "Family", "sortable": true, "searchable": true},
    {"key": "is_valid", "label": "Valid", "sortable": true, "format": "boolean"}
  ],
  "default_sort": {"key": "name", "direction": "asc"},
  "searchable": true,
  "on_row_click": {
    "action": "open_detail",
    "detail_view": "genus_detail",
    "id_column": "id"
  }
}
```

### 4.5 Tree View 정의 예시

```json
{
  "type": "tree",
  "title": "Taxonomy",
  "source_query": "taxonomy_tree",
  "icon": "bi-diagram-3",
  "tree_options": {
    "root_query": "taxonomy_tree",
    "build_from_flat": true,
    "id_field": "id",
    "parent_field": "parent_id",
    "label_field": "name",
    "item_query": "family_genera",
    "item_param": "family_id",
    "item_columns": [
      {"key": "name", "label": "Genus", "format": "italic"},
      {"key": "author", "label": "Author"},
      {"key": "year", "label": "Year"},
      {"key": "is_valid", "label": "Valid", "format": "boolean"}
    ],
    "on_node_info": {"action": "open_detail", "detail_view": "rank_detail"},
    "on_item_click": {"action": "open_detail", "detail_view": "genus_detail"},
    "item_valid_filter": {"column": "is_valid", "label": "Valid only"}
  }
}
```

### 4.6 Detail View 정의 예시

```json
{
  "type": "detail",
  "title": "Genus Detail",
  "source_query": "genus_detail",
  "id_param": "id",
  "sections": [
    {
      "type": "field_grid",
      "title": "Basic Information",
      "fields": [
        {"key": "name", "label": "Name", "format": "italic"},
        {"key": "author", "label": "Author"},
        {"key": "year", "label": "Year"},
        {"key": "is_valid", "label": "Valid", "format": "boolean"},
        {"key": "type_species", "label": "Type Species", "format": "italic"},
        {"key": "temporal_code", "label": "Temporal Range", "format": "temporal_range"},
        {"key": "hierarchy", "label": "Classification", "format": "hierarchy"}
      ]
    },
    {
      "type": "linked_table",
      "title": "Formations",
      "data_key": "formations",
      "columns": [
        {"key": "name", "label": "Formation"},
        {"key": "country", "label": "Country"},
        {"key": "period", "label": "Period"}
      ],
      "on_row_click": {"action": "open_detail", "detail_view": "formation_detail"}
    },
    {"type": "annotations"}
  ]
}
```

### 4.7 Field Formats

매니페스트에서 사용 가능한 필드 포맷:

| format | 렌더링 |
|--------|--------|
| `italic` | 이탤릭체 (학명 등) |
| `boolean` | 체크마크(✓) / 엑스(✗) |
| `link` | 클릭 가능한 하이퍼링크 |
| `color_chip` | 색상 칩 (hex color) |
| `code` | 모노스페이스 코드 |
| `hierarchy` | 계층 경로 (Class → Order → ... → Family) |
| `temporal_range` | 지질 시대 코드 + ICS 매핑 링크 |
| `computed` | 런타임 계산값 |

### 4.8 Section Types (Detail View)

| type | 설명 |
|------|------|
| `field_grid` | 키-값 필드 그리드 (2열 레이아웃) |
| `linked_table` | 연결된 데이터 테이블 (클릭 가능) |
| `tagged_list` | 태그 형태의 리스트 (지역, 형성층 등) |
| `raw_text` | 원본 텍스트 (raw_entry 등) |
| `annotations` | 사용자 주석 섹션 (Overlay DB) |
| `synonym_list` | 동의어 목록 (분류학 전용) |
| `rank_children` | 하위 분류군 목록 |
| `rank_statistics` | 하위 분류군 통계 |
| `bibliography` | 관련 참고문헌 |

---

## 5. SCODA Desktop 뷰어

### 5.1 구성 요소

SCODA Desktop은 다음 4개의 런타임 구성 요소로 이루어진다:

```
┌─────────────────────────────────────────────────────────┐
│                    SCODA Desktop                         │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  GUI (tkinter)│  │ Flask Server │  │  MCP Server   │  │
│  │              │  │   (port 8080)│  │  (stdio/SSE)  │  │
│  │  • 패키지 선택 │  │  • REST API  │  │  • 14개 도구   │  │
│  │  • Start/Stop │  │  • 정적 파일  │  │  • Evidence   │  │
│  │  • 로그 뷰어   │  │  • SPA 서빙  │  │    Pack 패턴  │  │
│  │  • SPA 추출   │  │  • CORS      │  │  • Overlay    │  │
│  │              │  │              │  │    R/W        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│         └─────────┬───────┘──────────────────┘           │
│                   ↓                                      │
│         ┌─────────────────┐                              │
│         │  scoda_package.py│  ← 중앙 DB 접근 모듈         │
│         │  PackageRegistry │                              │
│         └────────┬────────┘                              │
│                  ↓                                       │
│  ┌─────────────────────────────────────────────────┐     │
│  │          SQLite (3-DB ATTACH)                    │     │
│  │                                                  │     │
│  │  main: trilobase.db  (canonical, read-only)      │     │
│  │  overlay: trilobase_overlay.db  (user, read/write)│     │
│  │  pc: paleocore.db  (infrastructure, read-only)   │     │
│  └─────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 5.2 GUI 컨트롤 패널

Docker Desktop에서 영감을 받은 tkinter 기반 컨트롤 패널:

**기능:**
- **패키지 목록 (Listbox):** 탐색된 .scoda 패키지 표시, Running/Stopped 상태 아이콘
- **서버 제어:** Start Server / Stop Server 버튼
- **브라우저 오픈:** 서버 시작 후 자동 / 수동 브라우저 열기
- **SPA 추출:** Reference SPA가 포함된 패키지에서 SPA 추출
- **실시간 로그:** Flask 서버 로그를 색상별 레벨로 표시 (ERROR:빨강, WARNING:주황, INFO:파랑, SUCCESS:초록)
- **의존성 표시:** 실행 중인 패키지의 dependency를 들여쓰기 자식으로 표시

**실행 모드:**

| 모드 | 서버 실행 방식 | 로그 캡처 |
|------|-------------|----------|
| 개발 모드 | subprocess (별도 프로세스) | stdout 파이프 |
| Frozen 모드 (PyInstaller) | threading (동일 프로세스) | sys.stdout/stderr 리다이렉트 |

**패키지 전환 제약:** 서버가 실행 중일 때는 패키지 전환이 차단된다. 먼저 서버를 중지한 후 다른 패키지를 선택해야 한다.

### 5.3 Flask 웹 서버

`app.py` (1,120줄)는 다음을 제공한다:

**REST API 엔드포인트 (22개):**

| 범주 | 엔드포인트 | 설명 |
|------|----------|------|
| **탐색** | `GET /api/tree` | 전체 분류 계층 트리 |
| | `GET /api/family/<id>/genera` | Family의 Genus 목록 |
| | `GET /api/rank/<id>` | 분류군 상세 |
| | `GET /api/genus/<id>` | Genus 상세 (계층, 동의어, 산출지 포함) |
| **참조 데이터** | `GET /api/country/<id>` | 국가 상세 + 관련 genera |
| | `GET /api/region/<id>` | 지역 상세 + 관련 genera |
| | `GET /api/formation/<id>` | 지층 상세 + 관련 genera |
| | `GET /api/bibliography/<id>` | 참고문헌 상세 + 관련 genera |
| | `GET /api/chronostrat/<id>` | ICS 연대 단위 상세 |
| **SCODA 메타** | `GET /api/metadata` | 패키지 메타데이터 + 통계 |
| | `GET /api/provenance` | 데이터 출처 |
| | `GET /api/display-intent` | 뷰 타입 힌트 |
| | `GET /api/queries` | Named Query 목록 |
| | `GET /api/queries/<name>/execute` | Named Query 실행 |
| | `GET /api/manifest` | UI 매니페스트 |
| **범용** | `GET /api/detail/<query_name>` | Named Query 기반 범용 상세 |
| **PaleoCore** | `GET /api/paleocore/status` | PaleoCore DB 상태 + Cross-DB 검증 |
| **Overlay** | `GET /api/annotations/<type>/<id>` | 사용자 주석 조회 |
| | `POST /api/annotations` | 사용자 주석 추가 |
| | `DELETE /api/annotations/<id>` | 사용자 주석 삭제 |
| **정적** | `GET /` | 메인 페이지 (SPA 또는 generic viewer) |
| | `GET /<path>` | SPA 정적 파일 서빙 |

**CORS 지원:** 모든 응답에 `Access-Control-Allow-Origin` 헤더를 추가하여 외부 SPA에서의 접근을 허용한다.

**패키지 선택:** `--package` CLI 인자 또는 `set_active_package()` 호출로 활성 패키지를 지정한다. Flask는 항상 **하나의 패키지만** 서빙한다.

### 5.4 Generic 프론트엔드

`static/js/app.js` (1,399줄)는 매니페스트 기반의 범용 SCODA 뷰어이다:

**렌더링 파이프라인:**

```
1. loadManifest()           ← /api/manifest 호출
2. buildViewTabs()          ← manifest.views에서 탭 생성
3. switchToView(viewKey)    ← 탭 클릭 시
4. view.type에 따라 분기:
   ├── "tree"  → loadTree() → buildTreeFromFlat()
   ├── "table" → loadTableView() → renderTableView()
   └── "chart" → loadChartView() → renderChartView()
5. 행 클릭 시:
   on_row_click.action === "open_detail"
   → openDetail(detail_view, id)
   → renderDetailFromManifest(data, viewDef)
```

**특징:**
- **패키지 비종속:** Trilobase뿐 아니라 어떤 .scoda 패키지든 매니페스트만 있으면 자동으로 탭/테이블/상세 모달을 생성
- **Graceful degradation:** 매니페스트가 없으면 기존 레거시 UI로 폴백
- **패키지명 표시:** Navbar에 활성 패키지의 이름과 버전을 표시

---

## 6. Multi-DB 아키텍처

### 6.1 SQLite ATTACH 패턴

SCODA는 SQLite의 `ATTACH DATABASE` 기능을 활용하여 여러 패키지의 데이터를 하나의 커넥션에서 조회한다:

```sql
-- 메인 연결
conn = sqlite3.connect('trilobase.db')

-- Overlay DB 연결 (사용자 주석)
ATTACH DATABASE 'trilobase_overlay.db' AS overlay

-- PaleoCore DB 연결 (공유 인프라 데이터)
ATTACH DATABASE 'paleocore.db' AS pc
```

이를 통해 Cross-DB JOIN이 가능하다:

```sql
-- Trilobase genus_locations와 PaleoCore countries를 JOIN
SELECT g.name, c.name AS country
FROM genus_locations gl
JOIN taxonomic_ranks g ON gl.genus_id = g.id
JOIN pc.countries c ON gl.country_id = c.id
WHERE c.name = 'China';
```

### 6.2 PackageRegistry

`scoda_package.py`의 `PackageRegistry` 클래스는 패키지 탐색과 DB 연결을 중앙 관리한다:

```python
registry = PackageRegistry()
registry.scan("/path/to/packages/")  # *.scoda 파일 탐색

# 패키지 목록
for pkg in registry.list_packages():
    print(f"{pkg['name']} v{pkg['version']} ({pkg['record_count']} records)")

# DB 연결 (의존성 자동 ATTACH)
conn = registry.get_db("trilobase")
# → main: trilobase data.db
# → overlay: trilobase_overlay.db
# → pc: paleocore data.db (dependency)
```

**탐색 우선순위:**
1. `*.scoda` 파일 탐색 → ZIP에서 data.db 추출
2. .scoda가 없으면 `*.db` 파일 직접 사용 (폴백)

**의존성 해결:**
manifest.json의 `dependencies` 배열을 읽고, 같은 디렉토리에서 해당 .scoda 패키지를 찾아 `alias`로 ATTACH한다.

### 6.3 3-DB 역할 분리

| DB | Alias | 접근 | 역할 |
|----|-------|------|------|
| trilobase.db | (main) | Read-only | 분류학 데이터 (genus, synonym, bibliography) |
| trilobase_overlay.db | overlay | Read/Write | 사용자 주석 (annotation) |
| paleocore.db | pc | Read-only | 공유 인프라 (country, formation, ICS 연대) |

### 6.4 Logical Foreign Key

패키지 간 참조는 SQLite FOREIGN KEY 제약이 아닌 **논리적 FK**로 관리된다:

| Source (Trilobase) | Target (PaleoCore) | 참조 의미 |
|---|---|---|
| `genus_locations.country_id` | `pc.countries.id` | Genus 산출 국가 |
| `genus_locations.region_id` | `pc.geographic_regions.id` | Genus 산출 지역 |
| `genus_formations.formation_id` | `pc.formations.id` | Genus 산출 지층 |
| `taxonomic_ranks.temporal_code` | `pc.temporal_ranges.code` | Genus 지질 시대 |

---

## 7. Overlay DB와 Local Annotations

### 7.1 설계 원칙

SCODA의 핵심 원칙 중 하나는 **canonical 데이터의 불변성**이다. 그러나 과학자는 데이터에 대해 메모를 남기고, 대안적 해석을 기록하고, 외부 문헌 링크를 추가하고 싶어한다. Overlay DB는 이 두 가지 요구를 동시에 만족시킨다:

- Canonical 데이터는 절대 수정되지 않는다
- 사용자의 로컬 주석은 별도 파일에 저장된다
- 주석은 canonical 데이터와 함께 표시되지만, 시각적으로 구분된다

### 7.2 Overlay DB 스키마

```sql
-- 버전 추적
CREATE TABLE overlay_metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
-- key: 'canonical_version', 'created_at'

-- 사용자 주석
CREATE TABLE user_annotations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type     TEXT NOT NULL,      -- 'genus', 'family', 'order', ...
    entity_id       INTEGER NOT NULL,   -- canonical DB의 ID
    entity_name     TEXT,               -- 이름 (릴리스 간 매칭용)
    annotation_type TEXT NOT NULL,      -- 'note', 'correction', 'alternative', 'link'
    content         TEXT NOT NULL,
    author          TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 7.3 entity_name의 역할

`entity_id`는 canonical DB 버전마다 달라질 수 있다. 반면 `entity_name`(예: "Paradoxides")은 불변이다. Major 버전 업그레이드 시 entity_name으로 주석을 새 ID에 매핑할 수 있다.

### 7.4 Annotation Types

| type | 용도 | 예시 |
|------|------|------|
| `note` | 일반 메모 | "이 genus에 대해 Smith (2020) 참고할 것" |
| `correction` | 데이터 오류 지적 | "저자명이 잘못됨, 실제로는 ZHANG, 1981" |
| `alternative` | 대안적 분류 해석 | "Adrain (2011)에서 이 genus를 Aulacopleuridae로 재배치" |
| `link` | 외부 링크 | "https://paleobiodb.org/classic/displayReference?id=12345" |

### 7.5 버전 호환성

| Canonical 버전 변경 | Overlay 처리 | 주석 보존 |
|------------------|-----------|---------|
| PATCH (1.0.0 → 1.0.1) | 버전만 업데이트 | 전체 보존 |
| MINOR (1.0.0 → 1.1.0) | 버전만 업데이트 | 전체 보존 |
| MAJOR (1.0.0 → 2.0.0) | 재생성 + 마이그레이션 | entity_name 기반 매칭 |

---

## 8. MCP 서버 — LLM 통합 인터페이스

### 8.1 개요

MCP(Model Context Protocol) 서버는 LLM(대규모 언어 모델)이 SCODA 패키지의 데이터를 자연어로 쿼리할 수 있게 해주는 인터페이스이다.

**핵심 원칙: DB is truth, MCP is access, LLM is narration**

- LLM은 데이터를 판단하거나 정의하지 않는다
- LLM은 DB가 제공하는 증거를 서술할 뿐이다
- 모든 응답에는 출처(provenance)가 포함된다

### 8.2 14개 MCP 도구

| 범주 | 도구 | 설명 |
|------|------|------|
| **분류** | `get_taxonomy_tree` | 전체 분류 계층 트리 |
| | `get_rank_detail` | 분류군 상세 |
| | `get_family_genera` | Family의 Genus 목록 |
| **검색** | `search_genera` | Genus 이름 패턴 검색 |
| | `get_genera_by_country` | 국가별 Genus 조회 |
| | `get_genera_by_formation` | 지층별 Genus 조회 |
| **메타** | `get_metadata` | 패키지 메타데이터 + 통계 |
| | `get_provenance` | 데이터 출처 |
| | `list_available_queries` | Named Query 목록 |
| **쿼리** | `execute_named_query` | Named Query 실행 |
| **주석** | `get_annotations` | 사용자 주석 조회 |
| | `add_annotation` | 주석 추가 (Overlay DB) |
| | `delete_annotation` | 주석 삭제 |
| **상세** | `get_genus_detail` | Genus Evidence Pack |

### 8.3 Evidence Pack 패턴

`get_genus_detail`은 단순한 레코드가 아니라 **Evidence Pack**을 반환한다. 이는 LLM이 근거 기반 서술을 할 수 있게 구조화된 응답이다:

```json
{
  "genus": {
    "id": 42,
    "name": "Paradoxides",
    "author": "BRONGNIART",
    "year": 1822,
    "is_valid": true,
    "family": "Paradoxididae",
    "type_species": "Entomostracites paradoxissimus",
    "raw_entry": "PARADOXIDES BRONGNIART, 1822 ..."
  },
  "synonyms": [...],
  "formations": [...],
  "localities": [...],
  "references": [...],
  "provenance": {
    "source": "Jell & Adrain, 2002",
    "canonical_version": "2.1.0",
    "extraction_date": "2026-02-04"
  }
}
```

### 8.4 실행 모드

| 모드 | 프로토콜 | 용도 |
|------|---------|------|
| **stdio** | stdin/stdout | Claude Desktop에서 직접 실행 |
| **SSE** | HTTP (Starlette + uvicorn) | GUI에서 포트 8081로 실행 |

**stdio 모드 사용 (Claude Desktop 설정):**

```json
{
  "mcpServers": {
    "trilobase": {
      "command": "ScodaDesktop_mcp.exe"
    }
  }
}
```

---

## 9. 빌드 및 배포 파이프라인

### 9.1 배포 산출물

```
dist/
├── ScodaDesktop.exe        # GUI 뷰어 (Windows, console=False)
├── ScodaDesktop_mcp.exe    # MCP stdio 서버 (Windows, console=True)
├── trilobase.scoda         # Trilobase 데이터 패키지
└── paleocore.scoda         # PaleoCore 인프라 패키지
```

**사용자 배포:** 위 4개 파일을 같은 디렉토리에 놓고 `ScodaDesktop.exe`를 실행하면 된다. 별도 설치 불요.

### 9.2 빌드 프로세스

```
python scripts/build.py
    │
    ├── 1. PyInstaller로 EXE 빌드
    │   ├── ScodaDesktop.exe  ← scripts/gui.py 진입점
    │   │   번들: app.py, scoda_package.py, templates/, static/, spa/
    │   └── ScodaDesktop_mcp.exe ← mcp_server.py 진입점
    │       번들: scoda_package.py
    │
    ├── 2. trilobase.scoda 생성
    │   trilobase.db → ZIP(manifest.json + data.db + assets/spa/*)
    │
    └── 3. paleocore.scoda 생성
        paleocore.db → ZIP(manifest.json + data.db)
```

**핵심 설계:** EXE 안에 DB를 번들링하지 않는다. 데이터는 .scoda 패키지로 외부에 분리되어 있으며, EXE는 실행 시 같은 디렉토리의 .scoda 파일을 탐색한다.

### 9.3 릴리스 프로세스

```
1. 데이터 수정 + 테스트 (pytest, 230개)
2. artifact_metadata version 업데이트
3. scripts/release.py 실행 → releases/ 디렉토리에 패키징
4. Git commit + tag (v2.1.0)
5. scripts/build.py 실행 → dist/ 생성
6. GitHub Release 또는 직접 배포
```

**불변성 보장:** 같은 버전 번호로 릴리스를 재생성할 수 없다. `release.py`는 기존 디렉토리가 있으면 에러를 발생시킨다.

### 9.4 Semantic Versioning

| 유형 | 버전 예시 | 변경 내용 |
|------|----------|---------|
| PATCH | 1.0.0 → 1.0.1 | 데이터 오류 수정, 타이포 |
| MINOR | 1.0.0 → 1.1.0 | 데이터 추가, 새 테이블 |
| MAJOR | 1.0.0 → 2.0.0 | 스키마 변경, 테이블 삭제 |

---

## 10. Reference Implementation SPA

### 10.1 Generic Viewer vs. Reference SPA

SCODA Desktop은 두 종류의 프론트엔드를 구분한다:

| | Generic Viewer | Reference SPA |
|---|---|---|
| 위치 | `static/js/app.js` (EXE 내장) | `spa/` (패키지 내 `assets/spa/`) |
| 대상 | 모든 .scoda 패키지 | 특정 패키지 전용 |
| 의존성 | Jinja2 템플릿 | 독립 (순수 HTML/JS/CSS) |
| 커스텀 로직 | 없음 (매니페스트에만 의존) | 패키지 도메인 전용 함수 포함 |
| API 접근 | `/api/...` (same-origin) | `API_BASE + '/api/...'` (configurable) |

### 10.2 SPA 자동 전환

1. 사용자가 GUI에서 "Extract Reference SPA" 클릭
2. .scoda 패키지에서 `assets/spa/*` 파일을 `<name>_spa/` 디렉토리로 추출
3. Flask가 `<name>_spa/index.html`을 감지하면 자동으로 SPA 서빙으로 전환
4. SPA가 없으면 generic viewer(templates/index.html)로 폴백

### 10.3 Reference SPA 구성

```
spa/
├── index.html    # Jinja2 없는 독립 HTML
├── app.js        # API_BASE prefix 사용, 도메인 전용 함수 포함
└── style.css     # Rank 색상 등 도메인 전용 스타일
```

**API_BASE 패턴:**

```javascript
// spa/app.js
if (typeof API_BASE === 'undefined') var API_BASE = '';

// 모든 fetch 호출에서:
const response = await fetch(API_BASE + '/api/manifest');
```

이를 통해 SPA를 다른 서버에서 호스팅하면서 API만 SCODA Desktop을 가리킬 수 있다.

---

## 11. 참조 구현: Trilobase와 PaleoCore

### 11.1 Trilobase 패키지

삼엽충(trilobite) genus-level 분류학 데이터베이스. Jell & Adrain (2002) PDF에서 추출하여 정제.

**데이터 규모:**

| 항목 | 수량 |
|------|------|
| 분류군 (Class~Genus) | 5,340 |
| 유효 Genus | 4,260 (83.3%) |
| 무효 Genus (동의어 등) | 855 (16.7%) |
| 동의어 관계 | 1,055 |
| Genus-Formation 관계 | 4,853 |
| Genus-Country 관계 | 4,841 |
| 참고문헌 | 2,130 |

**분류 계층:**

```
Trilobita (Class, 1)
├── Agnostida (Order, 12개 중 하나)
│   ├── Agnostina (Suborder)
│   │   ├── Agnostoidea (Superfamily)
│   │   │   ├── Agnostidae (Family)
│   │   │   │   ├── Agnostus (Genus, 유효)
│   │   │   │   ├── Acadagnostus (Genus, 유효)
│   │   │   │   └── ...
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── ...
```

### 11.2 PaleoCore 패키지

고생물학 데이터베이스가 공통으로 필요로 하는 인프라 참조 데이터. Trilobase에서 분리하여 독립 패키지로 구성.

**데이터 규모:**

| 테이블 | 레코드 | 출처 |
|--------|--------|------|
| countries | 142 | Jell & Adrain (2002) |
| geographic_regions | 562 | 60 countries + 502 regions |
| cow_states | 244 | Correlates of War v2024 |
| country_cow_mapping | 142 | 수동 매핑 |
| formations | 2,004 | Jell & Adrain (2002) |
| temporal_ranges | 28 | 지질 시대 코드 |
| ics_chronostrat | 178 | ICS GTS 2020 (SKOS/RDF) |
| temporal_ics_mapping | 40 | 수동 매핑 |
| **합계** | **3,340** | |

**PaleoCore는 의존성이 없는 루트 패키지**이다. Trilobase가 PaleoCore에 의존하지만, PaleoCore는 독립적으로 사용할 수 있다. 향후 다른 고생물학 데이터베이스(예: 완족류, 두족류)도 같은 PaleoCore를 공유할 수 있다.

### 11.3 패키지 간 관계

```
                            ┌───────────────────┐
                            │    PaleoCore       │
                            │   (paleocore.scoda)│
                            │                    │
                            │  countries (142)   │
                            │  formations (2,004)│
                            │  ics_chronostrat   │
                            │  temporal_ranges   │
                            │  ...               │
                            └────────▲───────────┘
                                     │
                              ATTACH AS pc
                                     │
┌────────────────────────────────────┤
│                                    │
│    Trilobase (trilobase.scoda)     │
│                                    │
│    taxonomic_ranks (5,340) ────────┤ temporal_code → pc.temporal_ranges
│    synonyms (1,055)                │
│    bibliography (2,130)            │
│    genus_locations (4,841) ────────┤ country_id → pc.countries
│    genus_formations (4,853) ───────┤ formation_id → pc.formations
│                                    │
└────────────────────────────────────┘
```

---

## 12. 부록: 파일 구조 및 API 목록

### 12.1 프로젝트 파일 구조

```
trilobase/
├── scoda_package.py          # .scoda 패키지 + PackageRegistry + 중앙 DB 접근
├── app.py                    # Flask 웹 서버 (22개 엔드포인트, 1,120줄)
├── mcp_server.py             # MCP 서버 (14개 도구, stdio/SSE, 764줄)
├── scripts/
│   ├── gui.py                # GUI 컨트롤 패널 (tkinter, 859줄)
│   ├── serve.py              # CLI 서버 런처
│   ├── build.py              # PyInstaller 빌드 자동화
│   ├── create_scoda.py       # trilobase.db → trilobase.scoda
│   ├── create_paleocore.py   # trilobase.db → paleocore.db
│   └── create_paleocore_scoda.py  # paleocore.db → paleocore.scoda
├── templates/
│   └── index.html            # Generic viewer HTML (Jinja2)
├── static/
│   ├── css/style.css         # Generic viewer CSS (621줄)
│   └── js/app.js             # Generic viewer JS (1,399줄)
├── spa/                      # Reference Implementation SPA
│   ├── index.html
│   ├── app.js                # Full-featured JS (1,569줄)
│   └── style.css             # Domain-specific CSS (626줄)
├── examples/
│   └── genus-explorer/index.html  # 커스텀 SPA 예제
├── ScodaDesktop.spec         # PyInstaller 빌드 설정
├── trilobase.db              # Canonical SQLite DB (5.4 MB)
├── paleocore.db              # PaleoCore SQLite DB (332 KB)
├── test_app.py               # Flask 테스트 (213개)
├── test_mcp_basic.py         # MCP 기본 테스트 (1개)
├── test_mcp.py               # MCP 포괄적 테스트 (16개)
└── docs/
    ├── HANDOFF.md            # 프로젝트 현황
    ├── RELEASE_GUIDE.md       # 릴리스 가이드
    ├── SCODA_CONCEPT.md       # SCODA 개념 문서
    └── paleocore_schema.md    # PaleoCore 스키마 정의서
```

### 12.2 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| 데이터베이스 | SQLite 3 (ATTACH, Cross-DB JOIN) |
| 웹 서버 | Flask (WSGI) + CORS |
| MCP 서버 | mcp SDK + Starlette + uvicorn (ASGI) |
| GUI | tkinter (Python 표준 라이브러리) |
| 프론트엔드 | Vanilla JavaScript + Bootstrap 5 |
| 패키징 | PyInstaller (onefile, Windows/Linux) |
| 테스트 | pytest + pytest-asyncio (230개) |
| 패키지 포맷 | ZIP (확장자 .scoda) |

### 12.3 테스트 현황

| 파일 | 테스트 수 | 범위 |
|------|---------|------|
| `test_app.py` | 213 | Flask API, CORS, manifest, detail, SPA 서빙 |
| `test_mcp_basic.py` | 1 | MCP 서버 초기화 |
| `test_mcp.py` | 16 | MCP 14개 도구 + Evidence Pack |
| **합계** | **230** | |

---

**문서 끝.**
