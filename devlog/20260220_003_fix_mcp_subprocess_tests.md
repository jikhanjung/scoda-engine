# 003: MCP Subprocess 테스트 5건 실패 수정

**날짜:** 2026-02-20
**계획:** P04
**상태:** 완료

## 배경

`tests/test_mcp.py` 6개 테스트 중 5개가 실패. MCP subprocess(`python3 -m scoda_engine.mcp_server`)가 CWD 기반으로 .scoda/.db를 자동 탐색하는데, 테스트 환경에는 유효한 DB가 없어 빈 DB에 연결되었기 때문.

| 테스트 | 수정 전 | 수정 후 |
|--------|---------|---------|
| test_list_tools | PASSED | PASSED |
| test_get_metadata | FAILED | PASSED |
| test_get_provenance | FAILED | PASSED |
| test_list_available_queries | FAILED | PASSED |
| test_execute_named_query | FAILED | PASSED |
| test_annotations_lifecycle | FAILED | PASSED |

## 변경 내용

### 1. `scoda_engine/scoda_package.py` — `SCODA_DB_PATH` 환경변수 지원

`_resolve_paths()` 함수에 환경변수 체크를 추가. 기존 auto-discovery 로직 앞에 삽입하여, 환경변수가 설정된 경우 해당 경로를 canonical DB로 사용.

**경로 해석 우선순위 (변경 후):**
1. `_set_paths_for_testing()` 호출 (in-process 테스트용)
2. `SCODA_DB_PATH` 환경변수 (subprocess 테스트/CI용) ← **신규**
3. Frozen mode (PyInstaller)
4. Dev mode (프로젝트 루트 auto-discovery)

```python
env_db = os.environ.get('SCODA_DB_PATH')
if env_db:
    _canonical_db = os.path.abspath(env_db)
    name = os.path.splitext(os.path.basename(_canonical_db))[0]
    _overlay_db = os.path.join(os.path.dirname(_canonical_db), f'{name}_overlay.db')
    _resolve_dependencies(os.path.dirname(_canonical_db))
    return
```

기존 기능에 영향 없음: 일반 실행 환경에서 이 환경변수가 설정될 일이 없고, `_canonical_db is not None` 가드가 env var 체크보다 먼저 실행되므로 `_set_paths_for_testing()`과도 충돌 없음.

### 2. `tests/test_mcp.py` — `generic_db` fixture 활용

- `create_session(db_path)`: DB 경로 파라미터 추가, `StdioServerParameters(env={..., 'SCODA_DB_PATH': db_path})` 로 subprocess에 전달
- 6개 테스트 함수 모두 `generic_db` fixture 수신 → `db_path, _ = generic_db`
- `test_annotations_lifecycle`: generic fixture에 맞게 `genus` → `item`, `items_list` 쿼리 사용으로 변경

## 검증 결과

```
tests/test_mcp.py    6/6 passed (9.99s)
tests/ 전체         196/196 passed (103.83s) — regression 0건
```

## 변경 파일 목록

| 파일 | 변경 |
|------|------|
| `scoda_engine/scoda_package.py` | `_resolve_paths()`에 `SCODA_DB_PATH` env var 분기 추가, docstring 갱신 |
| `tests/test_mcp.py` | `create_session(db_path)` 시그니처 변경, 6개 테스트에 `generic_db` fixture 적용 |
