# P10: trilobase validate_manifest 중복 제거 계획

**작성일:** 2026-02-22
**선행:** S-3 (scoda-engine-core에 validate_manifest 모듈 이동 완료)

---

## 1. 현재 상태

S-3에서 `validate_manifest`, `validate_db`를 `scoda-engine-core`로 이동했으나,
trilobase 쪽에는 여전히 동일한 파일이 남아있어 중복 상태.

### trilobase 쪽 현황

**중복 파일:** `trilobase/scripts/validate_manifest.py` (~330줄, scoda-engine 버전과 동일)

**사용처 2곳:**

1. `scripts/create_scoda.py`
   ```python
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
   from validate_manifest import validate_db
   ```

2. `scripts/create_paleocore_scoda.py`
   ```python
   from validate_manifest import validate_db
   ```

**사용 패턴 (양쪽 동일):**
```python
errors, warnings = validate_db(db_path)
for w in warnings:
    print(f"  WARNING: {w}")
for e in errors:
    print(f"  ERROR: {e}", file=sys.stderr)
if errors:
    print(f"\nManifest validation failed: {len(errors)} error(s)", file=sys.stderr)
    sys.exit(1)
print(f"Manifest validation: OK ({len(warnings)} warning(s))")
```

### trilobase의 scoda-engine 의존성

```
# requirements.txt
-e /mnt/d/projects/scoda-engine[dev]
```

로컬 editable install이므로 scoda-engine-core도 이미 사용 가능.

---

## 2. 변경 계획

### Step 1: scripts/validate_manifest.py 삭제

trilobase의 `scripts/validate_manifest.py`를 삭제.

### Step 2: create_scoda.py 임포트 변경

**파일:** `scripts/create_scoda.py`

```python
# Before
from validate_manifest import validate_db

# After
from scoda_engine_core import validate_db
```

`sys.path.insert` 라인이 validate_manifest만을 위한 것이라면 함께 제거.
다른 로컬 임포트에도 사용 중이면 유지.

### Step 3: create_paleocore_scoda.py 임포트 변경

**파일:** `scripts/create_paleocore_scoda.py`

Step 2와 동일한 패턴 적용.

### Step 4: 동작 검증

```bash
cd /mnt/d/projects/trilobase
python scripts/create_scoda.py --dry-run      # 또는 실제 실행
python scripts/create_paleocore_scoda.py --dry-run
pytest tests/
```

---

## 3. 수정 파일 목록 (trilobase repo)

| 파일 | 변경 |
|------|------|
| `scripts/validate_manifest.py` | **삭제** |
| `scripts/create_scoda.py` | 임포트를 `scoda_engine_core`로 변경 |
| `scripts/create_paleocore_scoda.py` | 임포트를 `scoda_engine_core`로 변경 |

---

## 4. 리스크

- **없음**: trilobase는 이미 scoda-engine을 editable install로 사용 중이므로
  `scoda_engine_core` 임포트가 바로 동작함
- 사용 패턴(validate_db 호출 → errors/warnings 출력)이 동일하므로 동작 변경 없음
- 검증 로직 자체가 변경된 것이 아니라 임포트 경로만 변경

---

## 5. 비고

이 작업은 trilobase repo에서 진행해야 하며, scoda-engine repo 변경은 불필요.
