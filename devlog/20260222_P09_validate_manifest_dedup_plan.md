# P09: S-3 validate_manifest.py 중복 제거

**Date:** 2026-02-22
**Type:** Plan
**Task:** S-3

---

## Context

`validate_manifest.py`가 scoda-engine의 `scripts/`와 trilobase 프로젝트에 동일한 코드로 중복 존재한다.
S-2에서 `scoda-engine-core`를 순수 stdlib 패키지로 분리 완료했으므로, 검증 로직을 core로 이동하여
양쪽에서 `scoda-engine-core`를 임포트하도록 하는 것이 목표다.

### 적합성

`validate_manifest.py`는 `json`, `sqlite3`, `sys`, `os`만 사용 — core의 "zero dependencies, pure stdlib" 원칙에 완전히 부합.

---

## 현재 상태

- **위치:** `scripts/validate_manifest.py` (333줄)
- **역할:** `.scoda` 패키지의 `ui_manifest` JSON을 `ui_queries`와 대조하여 불일치 검출
- **테스트:** `tests/test_runtime.py` — `TestManifestValidator` 클래스 (13개 테스트)
- **임포트 방식:** `sys.path.insert(0, scripts_dir)` + `from validate_manifest import ...`

---

## 구현 계획

### Step 1: core에 validate_manifest 모듈 생성

**파일:** `core/scoda_engine_core/validate_manifest.py`

이동 대상:
- 상수: `KNOWN_VIEW_TYPES`, `KNOWN_SECTION_TYPES`, `TREE_REQUIRED_KEYS`, `CHART_REQUIRED_KEYS`
- Public 함수: `validate_manifest()`, `validate_db()`
- Private 함수: `_validate_view()`, `_validate_table_view()`, `_validate_tree_view()`, `_validate_chart_view()`, `_validate_hierarchy_view()`, `_validate_detail_view()`, `_collect_detail_view_refs()`

`main()` (CLI 진입점)은 core에 포함하지 않음 — scripts 래퍼에 유지.

### Step 2: core `__init__.py`에서 public API export

**파일:** `core/scoda_engine_core/__init__.py`

```python
from .validate_manifest import validate_manifest, validate_db
```

### Step 3: scripts/validate_manifest.py → thin wrapper

**파일:** `scripts/validate_manifest.py`

기존 333줄을 core 임포트 + `main()` CLI 래퍼로 교체. 실행 방식 동일 유지:
```bash
python scripts/validate_manifest.py <db_path>
```

### Step 4: 테스트 임포트 경로 수정

**파일:** `tests/test_runtime.py`

- Before: `sys.path.insert(0, scripts_dir)` + `from validate_manifest import validate_manifest, validate_db`
- After: `from scoda_engine_core import validate_manifest, validate_db`

### Step 5: 문서 업데이트

**파일:** `docs/HANDOFF.md`
- S-3 완료 상태 반영
- core public API에 validate 함수 추가 기록

---

## 수정 파일 요약

| 파일 | 변경 |
|------|------|
| `core/scoda_engine_core/validate_manifest.py` | **신규** — 검증 로직 이동 |
| `core/scoda_engine_core/__init__.py` | export 추가 |
| `scripts/validate_manifest.py` | thin wrapper로 교체 |
| `tests/test_runtime.py` | 임포트 경로 변경 |
| `docs/HANDOFF.md` | S-3 완료 반영 |

---

## 검증 방법

```bash
# 전체 225개 테스트 통과 확인
pytest tests/

# core에서 임포트 확인
python -c "from scoda_engine_core import validate_manifest, validate_db; print('OK')"
```
