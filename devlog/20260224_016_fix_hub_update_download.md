# Fix: Hub 업데이트 패키지 다운로드 안 되는 버그 수정

**Date:** 2026-02-24

## 증상

- Hub에서 trilobase 0.2.3 업데이트가 감지되어 UI에 표시됨
- Download 버튼 클릭 시 "already up to date" 메시지가 출력되며 다운로드가 진행되지 않음

## 원인

`hub_client.py`의 `resolve_download_order()` 함수가 **이름만 비교**하여 로컬에 같은 이름의 패키지가 있으면 버전과 무관하게 다운로드 목록에서 제외함.

```python
# Before (bug)
local_names = {pkg["name"] for pkg in local_packages}
...
if name not in local_names:       # 이름만 비교 → 구버전도 skip
    result.append(...)
```

`compare_with_local()`은 올바르게 버전 비교를 해서 updatable 목록에 넣지만, 실제 다운로드 시 호출되는 `resolve_download_order()`가 버전 비교 없이 skip하는 불일치가 원인.

## 수정

`resolve_download_order()`에 `_needs_download()` 헬퍼 추가. 로컬 패키지의 버전과 Hub 버전을 `_parse_semver()`로 비교하여, Hub 버전이 더 높으면 다운로드 목록에 포함.

```python
# After (fix)
local_map = {pkg["name"]: pkg.get("version", "") for pkg in local_packages}

def _needs_download(name, hub_version):
    if name not in local_map:
        return True
    local_ver = local_map[name]
    if not local_ver:
        return True
    try:
        return _parse_semver(hub_version) > _parse_semver(local_ver)
    except ValueError:
        return False
```

의존성 resolve 경로도 동일한 `_needs_download()` 로직을 적용.

## 변경 파일

- `core/scoda_engine_core/hub_client.py` — `resolve_download_order()` 버전 비교 로직 추가

## 테스트

- 전체 255 테스트 통과
