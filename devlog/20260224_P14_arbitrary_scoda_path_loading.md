# P14: 임의 경로 .scoda 패키지 로딩

**Date:** 2026-02-24
**Status:** Plan

---

## 1. 배경

현재 `.scoda` 패키지는 고정된 디렉토리(프로젝트 루트 또는 exe 디렉토리)에서만
자동 검색된다. 사용자가 파일 시스템의 임의 위치에 있는 `.scoda` 파일을 열 수
있어야 실제 사용이 가능하다.

### 현재 구조의 한계

| 진입점 | 현재 동작 | 한계 |
|--------|-----------|------|
| `app.py` | `--package <이름>` → base_path에서 검색 | 경로 지정 불가 |
| `serve.py` | `--package <이름>` → base_path에서 검색 | 경로 지정 불가 |
| `mcp_server.py` | `SCODA_DB_PATH` env (raw DB만) | `.scoda` 경로 불가 |
| `gui.py` | base_path 자동 스캔 | 외부 파일 열기 불가 |

---

## 2. 설계

### 2.1 Core: `PackageRegistry.register_path()`

`core/scoda_engine_core/scoda_package.py`에 추가:

```python
def register_path(self, scoda_path):
    """임의 경로의 .scoda 파일을 registry에 등록.

    - Overlay DB: .scoda 파일과 같은 디렉토리에 생성
    - Dependencies: 같은 디렉토리에서 탐색
    - 동일 이름 패키지 이미 존재 시 교체 (기존 close)

    Returns: 패키지 이름 (str)
    """
```

모듈 레벨 편의 함수:

```python
def register_scoda_path(scoda_path):
    """register_path + set_active_package 일괄 처리."""
```

`get_registry()` 업데이트:
- `SCODA_PACKAGE_PATH` 환경변수 지원 (`.scoda` 파일 경로)
- 설정 시 해당 파일을 registry에 등록 (디렉토리 scan 대신)

### 2.2 CLI: `--scoda-path` 인자

3개 진입점 모두에 동일 패턴 적용:

```bash
python -m scoda_engine.app --scoda-path /path/to/data.scoda
python -m scoda_engine.serve --scoda-path /path/to/data.scoda
python -m scoda_engine.mcp_server --scoda-path /path/to/data.scoda
```

`--scoda-path`가 `--package`보다 우선.

### 2.3 GUI: 파일 열기 + 드래그앤드롭

| 기능 | 구현 |
|------|------|
| 파일 열기 다이얼로그 | `tkinter.filedialog.askopenfilename()` |
| 드래그앤드롭 | `tkinterdnd2` (optional, 없으면 무시) |
| CLI 경로 전달 | `--scoda-path` argparse |
| 서브프로세스 전달 | 외부 경로 패키지 → `--scoda-path` 사용 |

- "Open .scoda File..." 버튼을 Controls 섹션에 추가
- 서버 실행 중이면 파일 열기 차단
- 등록 후 listbox 갱신 및 자동 선택

---

## 3. 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `core/scoda_engine_core/scoda_package.py` | `register_path()`, `register_scoda_path()`, `get_registry()` 업데이트 |
| `core/scoda_engine_core/__init__.py` | `register_scoda_path` export 추가 |
| `scoda_engine/app.py` | `--scoda-path` argparse 추가 |
| `scoda_engine/serve.py` | `--scoda-path` argparse 추가 |
| `scoda_engine/mcp_server.py` | `--scoda-path` argparse 추가 |
| `scoda_engine/gui.py` | 파일 열기 다이얼로그, D&D, `--scoda-path`, 서브프로세스 전달 |
| `tests/conftest.py` | `.scoda` 빌드 fixture 추가 |
| `tests/test_runtime.py` | `TestRegisterPath` 테스트 클래스 추가 |

---

## 4. 구현 순서

1. Core `register_path()` + `register_scoda_path()` + `get_registry()` 환경변수
2. Core `__init__.py` export
3. 테스트 fixture + `TestRegisterPath` (core 동작 검증)
4. CLI 진입점 3개 (`--scoda-path`)
5. GUI (파일 열기 + D&D + 서브프로세스 전달)

---

## 5. 검증

```bash
# 전체 테스트
pytest tests/

# 수동: CLI 임의 경로
python -m scoda_engine.app --scoda-path /tmp/test.scoda
python -m scoda_engine.serve --scoda-path /tmp/test.scoda
python -m scoda_engine.mcp_server --scoda-path /tmp/test.scoda

# 수동: GUI 파일 열기
python -m scoda_engine.gui --scoda-path /tmp/test.scoda
# GUI에서 "Open .scoda File..." 버튼으로 파일 선택
```
