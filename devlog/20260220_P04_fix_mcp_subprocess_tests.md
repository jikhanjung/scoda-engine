# P04: Fix MCP Subprocess Tests (5 failing)

**날짜:** 2026-02-20
**상태:** 완료 → 003에서 구현

## 배경

scoda-engine의 `tests/test_mcp.py` 6개 중 5개 테스트가 실패. 원인: MCP subprocess(`python3 -m scoda_engine.mcp_server`)가 CWD에서 .scoda/.db를 자동 탐색하지만, 테스트 환경에서는 유효한 DB가 없어 빈 DB에 연결됨.

- `test_list_tools`: PASSED (DB 없이도 tool 목록 반환 가능)
- `test_get_metadata`: FAILED (빈 DB → JSONDecodeError)
- `test_get_provenance`: FAILED
- `test_list_available_queries`: FAILED
- `test_execute_named_query`: FAILED
- `test_annotations_lifecycle`: FAILED

## 해결 방법

`SCODA_DB_PATH` 환경변수를 추가하여 subprocess에 테스트 DB 경로를 전달.

## 변경 파일

### 1. `scoda_engine/scoda_package.py` — `SCODA_DB_PATH` 환경변수 지원

`_resolve_paths()` 함수 시작 부분에 env var 체크 추가 (기존 auto-discovery 앞):

```python
# Check environment variable override (for testing/CI)
env_db = os.environ.get('SCODA_DB_PATH')
if env_db:
    _canonical_db = os.path.abspath(env_db)
    name = os.path.splitext(os.path.basename(_canonical_db))[0]
    _overlay_db = os.path.join(os.path.dirname(_canonical_db), f'{name}_overlay.db')
    _resolve_dependencies(os.path.dirname(_canonical_db))
    return
```

docstring 업데이트: priority 목록에 env var 추가.

### 2. `tests/test_mcp.py` — `generic_db` fixture 활용

- `conftest.py`의 기존 `generic_db` fixture를 import/사용
- `create_session(db_path)` 에 DB 경로 파라미터 추가
- `StdioServerParameters(env={..., 'SCODA_DB_PATH': db_path})` 로 전달
- 5개 테스트 함수에 `generic_db` fixture 인자 추가

## 검증

```bash
cd /mnt/d/projects/scoda-engine
pytest tests/test_mcp.py -v   # 6/6 통과 확인
pytest tests/ -v              # 전체 regression 없음 확인
```
