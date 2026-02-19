# SCODA Desktop MCP Server Guide

**Model Context Protocol (MCP) 서버 사용 가이드**

**버전:** 2.0.0

---

## 목차

- [개요](#개요)
- [설치 및 설정](#설치-및-설정)
- [MCP 도구 구조](#mcp-도구-구조)
- [Builtin 도구 (7개)](#builtin-도구-7개)
- [Dynamic 도구](#dynamic-도구)
- [사용 예시](#사용-예시)
- [SCODA 원칙](#scoda-원칙)
- [트러블슈팅](#트러블슈팅)

---

## 개요

SCODA Desktop MCP 서버는 **Model Context Protocol**을 통해 LLM이 `.scoda` 패키지의 데이터를 쿼리할 수 있게 합니다.

### 주요 특징

- **7개 Builtin 도구**: 모든 `.scoda` 패키지에서 공통으로 사용 가능 (metadata, provenance, queries, annotations)
- **Dynamic 도구**: `.scoda` 패키지의 `mcp_tools.json`에서 도메인별 도구를 동적 로드
- **도메인 무관(Domain-Agnostic)**: 런타임 코드에 도메인 전용 로직 없음
- **SCODA 원칙 준수**: DB is truth, MCP is access, LLM is narration

### 아키텍처

```
┌─────────────────┐
│   Claude/LLM    │ (자연어 쿼리)
└────────┬────────┘
         │ JSON-RPC (stdio)
         ▼
┌───────────────────────────────────┐
│  ScodaDesktop_mcp.exe             │
│  - 7 builtin tools (항상 제공)    │
│  - N dynamic tools (패키지별)     │
│  - SQL validation layer          │
└────────┬──────────────────────────┘
         │ Direct DB access
         ▼
┌───────────────────────────────────┐
│  .scoda Package                   │
│  ├── data.db (Canonical, R/O)    │
│  ├── manifest.json               │
│  └── mcp_tools.json (optional)   │
│                                   │
│  Overlay DB (R/W, annotations)   │
└───────────────────────────────────┘
```

### 두 개의 실행 파일

| 파일 | 용도 | 실행 방법 |
|------|------|----------|
| `ScodaDesktop.exe` | GUI 뷰어 (Flask 웹 서버 + 브라우저) | 더블클릭 또는 CLI |
| `ScodaDesktop_mcp.exe` | MCP stdio 서버 (Claude Desktop 전용) | Claude Desktop이 자동 spawn |

---

## 설치 및 설정

### 의존성 설치

**기본 (stdio 모드):**
```bash
pip install mcp>=1.0.0
```

**SSE 모드 추가:**
```bash
pip install mcp>=1.0.0 starlette uvicorn
```

### Claude Desktop 설정

#### 방법 1: ScodaDesktop_mcp.exe 사용 (권장)

**파일:** `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "scoda-desktop": {
      "command": "C:\\path\\to\\ScodaDesktop_mcp.exe"
    }
  }
}
```

#### 방법 2: Python source 사용 (개발자용)

**macOS/Linux:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "scoda-desktop": {
      "command": "python3",
      "args": ["-m", "scoda_engine.mcp_server"],
      "cwd": "/absolute/path/to/trilobase"
    }
  }
}
```

**설정 후 Claude Desktop을 재시작하세요.**

### MCP 서버 수동 실행

```bash
# stdio 모드 (기본)
python -m scoda_engine.mcp_server

# SSE 모드
python -m scoda_engine.mcp_server --mode sse --port 8081

# Health check
curl http://localhost:8081/health
```

---

## MCP 도구 구조

SCODA Desktop MCP 서버의 도구는 두 계층으로 나뉩니다:

| 계층 | 도구 수 | 출처 | 설명 |
|------|---------|------|------|
| **Builtin** | 7개 (고정) | 런타임 코드 | 모든 `.scoda` 패키지에 공통 |
| **Dynamic** | 패키지별 | `mcp_tools.json` | 도메인 전용 도구 |

**`list_tools` 호출 시**: Builtin 7개 + Dynamic N개가 합쳐져 반환됩니다.

---

## Builtin 도구 (7개)

모든 `.scoda` 패키지에서 항상 사용 가능한 범용 도구입니다.

### 1. `get_metadata`

SCODA artifact 메타데이터를 조회합니다.

**Parameters:** 없음

**응답:**
```json
{
  "artifact_id": "trilobase",
  "name": "Trilobase",
  "version": "1.0.0",
  "description": "A taxonomic database of trilobite genera",
  "license": "CC-BY-4.0",
  "created_at": "2026-02-04"
}
```

---

### 2. `get_provenance`

데이터 출처 정보를 조회합니다.

**Parameters:** 없음

**응답:**
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

### 3. `list_available_queries`

사용 가능한 Named Query 목록을 조회합니다.

**Parameters:** 없음

**응답:**
```json
[
  {
    "id": 1,
    "name": "taxonomy_tree",
    "description": "Get full taxonomy tree from Class to Family",
    "params_json": "{}",
    "created_at": "2026-02-05 10:00:00"
  }
]
```

---

### 4. `execute_named_query`

사전 정의된 Named Query를 실행합니다.

**Parameters:**
- `query_name` (string, required): 쿼리 이름
- `params` (object, optional): 쿼리 파라미터 (기본값: {})

**응답:**
```json
{
  "query": "taxonomy_tree",
  "columns": ["id", "name", "rank"],
  "row_count": 225,
  "rows": [...]
}
```

---

### 5. `get_annotations`

특정 Entity의 사용자 주석을 조회합니다.

**Parameters:**
- `entity_type` (string, required): `genus`, `family`, `order`, `suborder`, `superfamily`, `class`
- `entity_id` (integer, required): Entity ID

**응답:**
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

---

### 6. `add_annotation`

새로운 주석을 추가합니다 (Overlay DB에 쓰기).

**Parameters:**
- `entity_type` (string, required): Entity 타입
- `entity_id` (integer, required): Entity ID
- `entity_name` (string, required): Entity 이름 (릴리스 간 매칭용)
- `annotation_type` (string, required): `note`, `correction`, `alternative`, `link`
- `content` (string, required): 주석 내용
- `author` (string, optional): 작성자

**응답:** 생성된 annotation 객체

---

### 7. `delete_annotation`

주석을 삭제합니다.

**Parameters:**
- `annotation_id` (integer, required): annotation ID

**응답:**
```json
{
  "message": "Annotation with ID 1 deleted."
}
```

---

## Dynamic 도구

### 개요

`.scoda` 패키지에 `mcp_tools.json` 파일이 포함되어 있으면, 해당 도구들이 자동으로 MCP 서버에 등록됩니다. 이를 통해 **도메인 전용 MCP 도구를 런타임 코드 수정 없이** 패키지만으로 제공할 수 있습니다.

### mcp_tools.json 구조

```json
{
  "version": "1.0",
  "tools": [
    {
      "name": "search_genera",
      "description": "Search genera by name pattern",
      "input_schema": {
        "type": "object",
        "properties": {
          "name_pattern": {"type": "string", "description": "SQL LIKE pattern"},
          "limit": {"type": "integer", "description": "Max results", "default": 50}
        },
        "required": ["name_pattern"]
      },
      "query_type": "single",
      "sql": "SELECT id, name, author, year FROM taxonomic_ranks WHERE rank='Genus' AND name LIKE :name_pattern LIMIT :limit",
      "default_params": {"limit": 50}
    }
  ]
}
```

### 3가지 Query Type

| query_type | 설명 | 필수 필드 |
|-----------|------|----------|
| `single` | SQL을 직접 실행 | `sql` |
| `named_query` | `ui_queries` 테이블의 named query 실행 | `named_query`, `param_mapping` |
| `composite` | Manifest detail view의 복합 쿼리 실행 | `view_name`, `param_mapping` |

#### single 예시

```json
{
  "name": "search_genera",
  "query_type": "single",
  "sql": "SELECT id, name, author FROM taxonomic_ranks WHERE name LIKE :name_pattern LIMIT :limit",
  "default_params": {"limit": 50}
}
```

#### named_query 예시

```json
{
  "name": "get_genera_by_country",
  "query_type": "named_query",
  "named_query": "genera_by_country",
  "param_mapping": {"country": "country", "limit": "limit"},
  "default_params": {"limit": 50}
}
```

#### composite 예시

```json
{
  "name": "get_genus_detail",
  "query_type": "composite",
  "view_name": "genus_detail",
  "param_mapping": {"genus_id": "id"}
}
```

### SQL 보안

Dynamic 도구의 `single` 쿼리는 `_validate_sql()`로 검증됩니다:
- `SELECT`와 `WITH` 문만 허용
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE` 등은 거부
- 파라미터는 `:param` 바인딩으로 SQL injection 방지

### Trilobase mcp_tools.json 예시

Trilobase 패키지는 7개의 도메인 전용 도구를 `mcp_tools.json`으로 제공합니다:

| 도구 | query_type | 설명 |
|------|-----------|------|
| `get_taxonomy_tree` | single | 분류 계층 트리 |
| `search_genera` | single | 이름 패턴 검색 |
| `get_genus_detail` | composite | Genus 상세 (복합) |
| `get_rank_detail` | composite | Rank 상세 (복합) |
| `get_family_genera` | named_query | Family의 Genus 목록 |
| `get_genera_by_country` | named_query | 국가별 Genus |
| `get_genera_by_formation` | named_query | 지층별 Genus |

---

## 사용 예시

### Claude Desktop에서 자연어 쿼리

MCP 서버가 연결되면 Claude Desktop에서 자연어로 쿼리할 수 있습니다.

#### 1. 메타데이터 조회

**질문:** "이 데이터베이스에 대해 알려줘"

**Claude의 동작:**
1. `get_metadata` 도구 호출
2. 패키지 정보 분석 및 요약

---

#### 2. Named Query 활용

**질문:** "사용 가능한 쿼리 목록을 보여줘"

**Claude의 동작:**
1. `list_available_queries` 도구 호출
2. 쿼리 목록 정리

**후속 질문:** "taxonomy_tree 쿼리를 실행해줘"

**Claude의 동작:**
1. `execute_named_query` 도구로 쿼리 실행
2. 결과 요약

---

#### 3. Dynamic 도구 사용 (Trilobase 패키지)

**질문:** "Paradoxides에 대해 자세히 알려줘"

**Claude의 동작:**
1. `search_genera` (dynamic) 도구로 검색
2. `get_genus_detail` (dynamic) 도구로 복합 상세 조회
3. 출처 인용하여 서술

---

#### 4. 주석 워크플로우

```
1. "Agnostus의 Formation 정보를 보여줘"
   → execute_named_query 또는 dynamic 도구

2. "Agnostus에 correction 주석 추가: 'Formation name needs verification'"
   → add_annotation

3. "Agnostus에 대한 내 주석을 보여줘"
   → get_annotations

4. "주석 5번을 삭제해줘"
   → delete_annotation
```

---

## SCODA 원칙

### 핵심 원칙

#### 1. DB is truth
- 데이터베이스가 유일한 진실의 원천
- LLM은 DB 데이터만 사용

#### 2. MCP is access
- MCP는 접근 수단일 뿐
- 데이터를 변경하지 않음 (Annotation 제외)

#### 3. LLM is narration
- LLM은 증거 기반 서술만 수행
- 판단이나 정의를 내리지 않음
- 항상 출처를 인용

### 올바른 사용 패턴

**출처 인용:**
> According to Jell & Adrain (2002), Paradoxides...

**불확실성 명시:**
> The database lists this as Middle Cambrian, though the exact age is not specified.

**데이터 기반 서술:**
> Based on the formation data, this genus has been found in Czech Republic and Morocco.

### Non-Goals (LLM이 해서는 안 되는 것)

- 분류학적 판단이나 정의 (DB에 없는 정보)
- 자율적 의사결정이나 계획
- 데이터베이스 쓰기 (주석 제외)

---

## 트러블슈팅

### 문제 1: MCP 서버가 연결되지 않음

**증상:** Claude Desktop에서 도구가 보이지 않음

**확인 사항:**
1. 설정 파일 경로: `%APPDATA%\Claude\claude_desktop_config.json` (Windows)
2. 절대 경로 사용 (상대 경로 불가)
3. `.scoda` 또는 `.db` 파일이 실행 파일과 같은 디렉토리에 있는지 확인
4. Claude Desktop 재시작

---

### 문제 2: "Database not found" 오류

**원인:** MCP 서버가 데이터 파일을 찾지 못함

**해결:**
1. `.scoda` 패키지 또는 `.db` 파일이 작업 디렉토리에 있는지 확인
2. Python source 사용 시 `cwd` 설정 확인

---

### 문제 3: Dynamic 도구가 로드되지 않음

**원인:** `.scoda` 패키지에 `mcp_tools.json`이 없음

**확인:**
```bash
# .scoda 파일 내용 확인
python -c "
import zipfile
with zipfile.ZipFile('trilobase.scoda') as z:
    print(z.namelist())
"
# mcp_tools.json이 목록에 있어야 함
```

**해결:**
```bash
# mcp_tools.json 포함하여 .scoda 재생성
python scripts/create_scoda.py --mcp-tools data/mcp_tools_trilobase.json
```

---

### 문제 4: Overlay DB 쓰기 오류

**증상:** 주석 추가 시 "read-only database" 오류

**해결:**
1. Overlay DB 파일 권한 확인: `chmod 644 trilobase_overlay.db`
2. Overlay DB가 자동 생성되지 않으면 서버 재시작

---

### 문제 5: SQL validation 오류

**증상:** Dynamic 도구 실행 시 "SQL validation failed" 오류

**원인:** `mcp_tools.json`의 SQL이 SELECT/WITH가 아닌 문 포함

**해결:** `mcp_tools.json`의 SQL을 수정하여 읽기 전용 쿼리만 사용

---

## 참고 자료

### 공식 문서

- **MCP 프로토콜**: https://modelcontextprotocol.io/
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop 설정**: https://modelcontextprotocol.io/clients/claude-desktop

### SCODA Desktop 문서

- [API Reference](API_REFERENCE.md) — REST API 레퍼런스
- [SCODA Concept](SCODA_CONCEPT.md) — SCODA 개념 설명
- [Handoff](HANDOFF.md) — 프로젝트 현황

---

## 버전 히스토리

- **v2.0.0** (2026-02-14): Domain-agnostic MCP Server (Phase 46)
  - Legacy 도메인 함수 7개 제거
  - Builtin 7개 + Dynamic N개 2계층 구조
  - Dynamic 도구: `.scoda` 내 `mcp_tools.json`에서 자동 로드
  - 3가지 query_type: `single`, `named_query`, `composite`
  - SQL validation layer (SELECT/WITH만 허용)
  - Server name: `"scoda-desktop"`

- **v1.3.0** (2026-02-10): EXE 분리
  - `ScodaDesktop.exe` (GUI) + `ScodaDesktop_mcp.exe` (MCP stdio)
  - Claude Desktop 설정 단순화

- **v1.1.0** (2026-02-10): SSE 모드 추가
  - SSE 전송 모드 지원 + Health check 엔드포인트

- **v1.0.0** (2026-02-09): Initial release
  - 14 hardcoded tools (legacy)
  - Evidence Pack pattern
  - stdio 모드

---

**Last Updated:** 2026-02-14
