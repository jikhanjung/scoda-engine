# 014: Hub 패키지 자동 체크 및 다운로드 구현

**Date:** 2026-02-24
**Plan:** P16
**Status:** Complete

---

## 변경 요약

ScodaDesktop 기동 시 Hub index를 백그라운드로 확인하여 새로운/업데이트 가능한
패키지를 표시하고, 사용자가 원클릭 다운로드할 수 있는 기능을 구현했다.
Core 모듈은 순수 stdlib로, GUI와 분리된 구조.

---

## 변경 파일 및 내용

### 1. `core/scoda_engine_core/hub_client.py` (신규, ~200줄)

순수 stdlib Hub 클라이언트 모듈.

**예외 클래스:**
- `HubError` — 기본 예외
- `HubConnectionError(HubError)` — 네트워크/파싱 실패
- `HubChecksumError(HubError)` — SHA-256 불일치

**공개 함수:**

| 함수 | 역할 |
|------|------|
| `fetch_hub_index(hub_url, timeout)` | index.json HTTP fetch + JSON parse. URL 우선순위: 인자 > `SCODA_HUB_URL` 환경변수 > 하드코딩 기본값 |
| `compare_with_local(hub_index, local_packages)` | Hub vs 로컬 비교. `_parse_semver` 재사용하여 semver 비교. 반환: `{available, updatable, up_to_date}` |
| `download_package(url, dest_dir, sha256, progress_cb, timeout)` | `.tmp` 파일에 청크(8KB) 쓰기 → SHA-256 검증 → rename. 실패 시 `.tmp` 자동 정리 |
| `resolve_download_order(hub_index, pkg_name, local_packages)` | 재귀적 의존성 해결. dependency-first 순서 반환. 로컬 보유분 스킵. 순환 의존성 safe (visited set) |

**설계 결정:**
- `scoda_package._parse_semver`을 import하여 semver 비교 로직 재사용
- `download_package`는 `tempfile.mkstemp` + `os.rename` 패턴으로 부분 파일 방지
- `progress_callback(bytes_downloaded, total_bytes)` 시그니처로 GUI 프로그레스 바 연동

### 2. `core/scoda_engine_core/__init__.py` (수정)

Hub 관련 7개 심볼 re-export 추가:
```python
from .hub_client import (
    fetch_hub_index, compare_with_local, download_package,
    resolve_download_order,
    HubError, HubConnectionError, HubChecksumError,
)
```

### 3. `tests/test_hub_client.py` (신규, 25 테스트)

모든 테스트는 `unittest.mock`으로 네트워크 호출을 모킹. 실제 HTTP 없음.

| 클래스 | 테스트 수 | 커버리지 |
|--------|-----------|----------|
| `TestCompareWithLocal` | 8 | available, updatable, up_to_date, local_newer, mixed, empty, no_url, semver_patch |
| `TestResolveDownloadOrder` | 7 | no_deps, with_dep, dep_already_local, already_local, not_in_hub, dep_not_in_hub, circular_deps |
| `TestFetchHubIndex` | 4 | success, network_error, invalid_json, env_var |
| `TestDownloadPackage` | 5 | success+checksum, checksum_mismatch, network_error, progress_callback, no_sha256 |
| `TestExceptions` | 1 | 예외 계층 확인 |

### 4. `scoda_engine/gui.py` (수정)

**Import 추가:**
- `from tkinter import ttk` (프로그레스 바)
- `from scoda_engine_core.hub_client import ...` (Hub 함수/예외)

**`__init__` 변경:**
- Hub 상태 변수 4개: `_hub_index`, `_hub_available`, `_hub_updatable`, `_download_in_progress`
- DnD 설정 후 `threading.Thread(target=self._fetch_hub_index).start()`

**`_create_widgets()` 변경:**
- Log 프레임 앞에 "Hub - Available Packages" `LabelFrame` 추가 (초기 미표시)
- 내부: `Listbox` (3줄) + `Download` 버튼 + 상태 라벨 + `ttk.Progressbar` (다운로드 시에만 표시)

**새 메서드 (10개):**

| 메서드 | 실행 스레드 | 역할 |
|--------|-------------|------|
| `_fetch_hub_index()` | 백그라운드 | Hub fetch + compare → `root.after()` 콜백 |
| `_on_hub_fetch_complete()` | 메인 | Hub 섹션 표시, 리스트 갱신, 로그 |
| `_on_hub_fetch_error()` | 메인 | 경고 로그 (섹션 숨김 유지) |
| `_refresh_hub_listbox()` | 메인 | `[UPD]`/`[NEW]` 라벨 + 버전 + 크기로 Listbox 채우기 |
| `_format_size()` | (정적) | 바이트 → "1.2 MB" 포맷 |
| `_download_selected_hub_package()` | 메인 | Download 버튼 핸들러. 선택 검증 → 스레드 시작 |
| `_do_download()` | 백그라운드 | `resolve_download_order` → 순차 다운로드 → `register_path` |
| `_update_download_progress()` | 메인 | 프로그레스 바 갱신 |
| `_on_download_complete()` | 메인 | 패키지 등록, 리스트 갱신, Hub 재비교 |
| `_on_download_error()` | 메인 | 정리 + 에러 다이얼로그 |

**다운로드 위치:** `registry._scan_dir` (frozen: exe 디렉토리, dev: 프로젝트 루트)

### 5. `ScodaDesktop.spec` (수정)

ScodaDesktop Analysis의 `hiddenimports`에 `'scoda_engine_core.hub_client'` 추가.

---

## 테스트 결과

```
pytest tests/test_hub_client.py tests/test_runtime.py tests/test_mcp_basic.py -v
→ 249 passed (25 hub_client + 189 runtime + 1 mcp_basic + 34 mcp)
```

기존 테스트 전부 통과, 신규 25개 추가.

---

## 주의사항 / 향후 작업

- Hub 섹션은 네트워크 없을 때 자동 숨김 — 오프라인 환경에서 정상 동작
- 업데이트 시 구버전 `.scoda` 파일 자동 삭제 미구현 (register_path가 메모리상 교체)
- 다운로드 취소 UI 미구현
- CLI 통합 (`--hub-download` 등)은 향후 필요 시 `hub_client.py` 재사용
- `test_mcp.py` 5개 실패는 기존 이슈 (subprocess MCP 테스트, `.scoda` CWD 필요)
