# P16: Hub 패키지 자동 체크 및 다운로드 설계

**Date:** 2026-02-24
**Status:** Approved → Implemented

---

## 1. 배경

P15에서 SCODA Hub 정적 레지스트리 인프라(index.json 생성 + Pages 배포)를 구현했다.
이제 ScodaDesktop.exe가 기동될 때 Hub index를 확인하여 사용 가능한 패키지를 보여주고,
사용자가 다운로드할 수 있게 해야 한다.

Hub URL: `https://jikhanjung.github.io/scoda-engine/index.json`
(`SCODA_HUB_URL` 환경변수로 override 가능)

---

## 2. 아키텍처

```
hub_client.py (core, 순수 stdlib)     gui.py (Tkinter UI)
┌──────────────────────────┐          ┌──────────────────────┐
│ fetch_hub_index()        │◄─────────│ 기동 시 백그라운드    │
│ compare_with_local()     │          │ 스레드에서 호출       │
│ download_package()       │◄─────────│ Download 버튼 클릭   │
│ resolve_download_order() │          │ 시 스레드에서 호출    │
└──────────────────────────┘          └──────────────────────┘
```

- **Core** (`hub_client.py`): HTTP fetch, 비교, 다운로드, 의존성 해결 — 순수 stdlib
- **GUI** (`gui.py`): Hub UI 섹션, 백그라운드 스레드, 프로그레스 바

---

## 3. 변경 범위

### Step 1: `core/scoda_engine_core/hub_client.py` (신규)

순수 stdlib Hub 클라이언트. 4개 공개 함수 + 예외 클래스:

```python
# 예외
class HubError(Exception): pass
class HubConnectionError(HubError): pass
class HubChecksumError(HubError): pass

# 함수
def fetch_hub_index(hub_url=None, timeout=10) -> dict
def compare_with_local(hub_index, local_packages) -> dict
def download_package(download_url, dest_dir, expected_sha256=None,
                     progress_callback=None, timeout=60) -> str
def resolve_download_order(hub_index, package_name, local_packages) -> list
```

| 함수 | 역할 |
|------|------|
| `fetch_hub_index` | index.json fetch + parse. 기본 URL: `SCODA_HUB_URL` 환경변수 또는 하드코딩 |
| `compare_with_local` | Hub vs 로컬 비교. 반환: `{available, updatable, up_to_date}` |
| `download_package` | .scoda 다운로드. 청크(8KB) 읽기 + SHA-256 검증. `.tmp` → rename 패턴 |
| `resolve_download_order` | 의존성 포함 다운로드 순서 결정 (dependency-first). 로컬 보유분 스킵 |

### Step 2: `core/scoda_engine_core/__init__.py` — export 추가

### Step 3: `tests/test_hub_client.py` (신규)

GUI 건드리기 전에 core 로직 먼저 테스트:
- `compare_with_local` — 순수 함수 테스트 (available, updatable, up_to_date, 혼합 등)
- `resolve_download_order` — 의존성 해결 순서, 순환 의존성, 로컬 보유 스킵
- `fetch_hub_index` — urllib mock으로 fetch/에러/env var 테스트
- `download_package` — urllib mock으로 다운로드 + SHA-256 검증/불일치

### Step 4: `scoda_engine/gui.py` — Hub UI 섹션 추가

- `__init__`: Hub 상태 변수 + 백그라운드 스레드로 `fetch_hub_index()` 호출
- `_create_widgets()`: "Hub - Available Packages" LabelFrame (초기 숨김)
  - Hub Listbox (높이 3줄) + Download 버튼 + 상태 라벨 + `ttk.Progressbar`
- 새 메서드: `_fetch_hub_index()`, `_on_hub_fetch_complete()/_error()`,
  `_refresh_hub_listbox()`, `_download_selected_hub_package()`,
  `_do_download()`, `_update_download_progress()`, `_on_download_complete()/_error()`

### Step 5: `ScodaDesktop.spec` — hidden imports 추가

---

## 4. 에러 처리

| 상황 | 동작 |
|------|------|
| 네트워크 없음 / Hub 접속 불가 | 로그에 경고, Hub 섹션 숨김, 로컬 패키지 정상 동작 |
| 다운로드 중 네트워크 끊김 | .tmp 파일 삭제, 에러 다이얼로그, 버튼 재활성화 |
| SHA-256 불일치 | 파일 삭제, HubChecksumError, 에러 다이얼로그 |
| Hub에 패키지 없음 (로컬만 있음) | "all packages up to date" 로그 |

---

## 5. 1차 범위 제한

- 업데이트 시 구버전 파일 자동 삭제는 안 함 (register_path가 메모리상 교체)
- 다운로드 취소 버튼 없음
- index.json 캐싱 없음 (매 기동 시 fresh fetch)
- Hub URL 단일 소스
- CLI 통합은 이번 범위 외 (core 모듈은 재사용 가능하게 작성)

---

## 6. 검증 계획

```bash
# 단위 테스트
pytest tests/test_hub_client.py -v

# 전체 테스트 (기존 224개 + 신규)
pytest tests/ -v

# 수동 테스트
python launcher_gui.py   # Hub 섹션이 나타나는지 확인
```
