# 012: 임의 경로 .scoda 패키지 로딩 구현

**Date:** 2026-02-24
**Plan:** P14
**Status:** Complete

---

## 변경 요약

`.scoda` 파일을 파일 시스템 어디에서든 열 수 있도록 Core, CLI, GUI 전체를 확장했다.

---

## 변경 파일 및 내용

### 1. Core: `PackageRegistry.register_path()` 추가

**`core/scoda_engine_core/scoda_package.py`**

- `PackageRegistry.register_path(scoda_path)` 메서드 추가
  - `.scoda` 파일을 열어 `_packages`에 등록
  - Overlay DB는 `.scoda`와 같은 디렉토리에 생성
  - dependencies도 같은 디렉토리에서 탐색 (exact name → versioned pattern)
  - 동일 이름 패키지 이미 존재 시 기존 close 후 교체
  - 반환: 패키지 이름(str)

- `register_scoda_path(scoda_path)` 모듈 레벨 편의 함수 추가
  - `PackageRegistry` lazy 생성 (디렉토리 scan 없이)
  - `register_path()` + `set_active_package()` 일괄 처리

- `get_registry()` 업데이트
  - `SCODA_PACKAGE_PATH` 환경변수 지원
  - 설정 시 해당 `.scoda` 파일을 registry에 등록 (기존 디렉토리 scan 대신)

### 2. Core export

**`core/scoda_engine_core/__init__.py`**

- `register_scoda_path` export 추가

### 3. CLI 진입점: `--scoda-path` 인자

**`scoda_engine/app.py`**, **`scoda_engine/serve.py`**, **`scoda_engine/mcp_server.py`**

- 3개 파일 모두 `--scoda-path` argparse 인자 추가
- `--scoda-path`가 `--package`보다 우선 처리
- `register_scoda_path()` 호출로 즉시 등록 + 활성화

### 4. GUI: 파일 열기 다이얼로그 + 드래그앤드롭

**`scoda_engine/gui.py`**

- `__init__`에 `scoda_path=None` 매개변수 추가
  - 전달받으면 `registry.register_path()`로 즉시 등록
  - `_external_scoda_paths` dict로 외부 로딩 경로 추적

- "Open .scoda File..." 버튼 추가 (Controls 섹션, Clear Log 위)
  - `_open_scoda_file()`: `filedialog.askopenfilename()` → `_load_scoda_from_path()`
  - 서버 실행 중이면 차단 (경고 메시지)

- `_load_scoda_from_path(path)`:
  - `registry.register_path()` → packages 갱신 → listbox 리프레시 → 자동 선택

- 드래그앤드롭: `tkinterdnd2` 사용 (optional dependency)
  - import 성공 시 `drop_target_register()` + `dnd_bind('<<Drop>>')`
  - import 실패 시 무시 (기능 미활성화)
  - 브레이스 감싸진 경로 처리 (`{/path/with spaces/file.scoda}`)

- `_start_server_subprocess()`:
  - 외부 경로 패키지이면 `--scoda-path` 전달 (기존은 `--package`)

- `main()`: `--scoda-path` argparse 추가

### 5. 테스트

**`tests/conftest.py`**

- `generic_scoda_package` fixture 추가
  - `generic_db`에서 `.scoda` 패키지 빌드 (ScodaPackage.create)

**`tests/test_runtime.py`**

- `TestRegisterPath` 클래스 추가 (5개 테스트):
  - `test_register_path_basic` — 로드 및 list_packages 확인
  - `test_register_path_get_db` — register → get_db → 쿼리 실행
  - `test_register_path_file_not_found` — FileNotFoundError
  - `test_register_path_replaces_existing` — 동일 이름 교체
  - `test_register_scoda_path_convenience` — 편의 함수 + active package 설정

---

## 테스트 결과

```
224 passed in 112.16s
```

- 기존 219 테스트 전부 통과
- 신규 5개 테스트 (`TestRegisterPath`) 전부 통과

---

## 버전 업

P14 작업 완료 후 Desktop 패키지 버전을 `0.1.0` → `0.1.1`로 올림.

| 파일 | 변경 |
|------|------|
| `scoda_engine/__init__.py` | `__version__ = "0.1.1"` |
| `pyproject.toml` | `version = "0.1.1"` |

---

## 사용법

```bash
# CLI: 임의 경로 .scoda 로딩
python -m scoda_engine.app --scoda-path /path/to/data.scoda
python -m scoda_engine.serve --scoda-path /path/to/data.scoda
python -m scoda_engine.mcp_server --scoda-path /path/to/data.scoda

# GUI: CLI에서 직접 지정
python -m scoda_engine.gui --scoda-path /path/to/data.scoda

# GUI: 실행 후 버튼으로 열기
# "Open .scoda File..." 버튼 클릭 → 파일 선택

# 환경변수
SCODA_PACKAGE_PATH=/path/to/data.scoda python -m scoda_engine.app
```
