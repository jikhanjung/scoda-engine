# S-3: validate_manifest.py 중복 제거 — 구현 완료

**Date:** 2026-02-22
**Type:** Implementation
**Plan:** `devlog/20260222_P09_validate_manifest_dedup_plan.md`

---

## 변경 요약

`scripts/validate_manifest.py`의 검증 로직을 `scoda-engine-core`로 이동하여,
trilobase 등 외부 프로젝트가 `from scoda_engine_core import validate_manifest, validate_db`로
임포트할 수 있도록 중복을 제거.

### 변경 내용

| 변경 | 설명 |
|------|------|
| 검증 로직 core 이동 | 상수 4개 + 함수 9개를 `core/scoda_engine_core/validate_manifest.py`로 이동 |
| Public API export | `validate_manifest`, `validate_db` 두 함수를 core `__init__.py`에서 re-export |
| scripts 래퍼 교체 | `scripts/validate_manifest.py`를 core 임포트 thin wrapper로 교체 (CLI `main()`만 유지) |
| 테스트 임포트 수정 | `from validate_manifest import ...` → `from scoda_engine_core import ...` |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `core/scoda_engine_core/validate_manifest.py` | **신규** — 순수 검증 로직 (stdlib만 사용) |
| `core/scoda_engine_core/__init__.py` | `validate_manifest`, `validate_db` re-export 추가 |
| `scripts/validate_manifest.py` | core 임포트 thin wrapper로 교체 |
| `tests/test_runtime.py` | 임포트 경로를 `scoda_engine_core`로 변경 |
| `docs/HANDOFF.md` | S-3 완료 반영 |

## 설계 원칙

- **zero dependencies 유지**: `validate_manifest.py`는 `json`, `sqlite3`, `os`만 사용 → core 원칙 적합
- **CLI 동작 보존**: `python scripts/validate_manifest.py <db>` 동일하게 동작
- **하위 호환**: `scripts/` 경로의 `sys.path` 임포트는 release.py 용도로 유지

## 테스트 결과

```
225 passed in 62.10s
```
