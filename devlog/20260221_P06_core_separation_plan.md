# P06: scoda-engine-core 분리 계획

**작성일:** 2026-02-21

---

## 1. 개요

scoda-engine에서 순수 라이브러리 부분(`scoda_package.py`)을 `scoda-engine-core`로
분리하여 PyPI 배포 가능한 독립 패키지로 만든다.

### 결정 사항

| 질문 | 결정 |
|------|------|
| Repo 구조 | **Monorepo** — 같은 git repo에 core/와 desktop 공존 |
| Core Python import 이름 | **`scoda_engine_core`** — PyPI명과 일치 |
| FastAPI/MCP 서버 위치 | **Desktop** — Core는 순수 stdlib만 의존 |

---

## 2. 목표 디렉토리 구조

```
scoda-engine/                          # git root (unchanged)
├── core/                              # NEW — core library package
│   ├── pyproject.toml                 # name = "scoda-engine-core"
│   └── scoda_engine_core/             # importable as scoda_engine_core
│       ├── __init__.py                # re-exports public API
│       └── scoda_package.py           # MOVED from scoda_engine/scoda_package.py
├── scoda_engine/                      # desktop/server package (MODIFIED)
│   ├── __init__.py
│   ├── scoda_package.py               # backward-compat shim → scoda_engine_core
│   ├── app.py                         # import from scoda_engine_core
│   ├── mcp_server.py                  # import from scoda_engine_core
│   ├── gui.py                         # import from scoda_engine_core
│   ├── serve.py                       # import from scoda_engine_core
│   ├── templates/index.html
│   └── static/{css,js}/
├── scripts/release.py                 # import from scoda_engine_core
├── tests/                             # import from scoda_engine_core
├── pyproject.toml                     # add scoda-engine-core dependency
├── ScodaDesktop.spec                  # add hiddenimports
├── CLAUDE.md
└── README.md
```

---

## 3. Core 패키지 설계

### 3.1 `core/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "scoda-engine-core"
version = "0.1.0"
description = "SCODA Core — pure-stdlib library for .scoda data packages"
requires-python = ">=3.10"
dependencies = []

[tool.setuptools.packages.find]
include = ["scoda_engine_core*"]
```

### 3.2 `core/scoda_engine_core/__init__.py`

```python
"""scoda_engine_core — pure-stdlib library for .scoda data packages."""

from .scoda_package import (
    ScodaPackage, PackageRegistry,
    get_db, ensure_overlay_db, get_canonical_db_path, get_overlay_db_path,
    get_scoda_info, get_mcp_tools,
    set_active_package, get_active_package_name, get_registry,
    _set_paths_for_testing, _reset_paths, _reset_registry,
)
```

### 3.3 Backward-compat shim (`scoda_engine/scoda_package.py`)

```python
"""
Backward-compatibility shim.
All core functionality has moved to scoda_engine_core.scoda_package.
"""
import scoda_engine_core.scoda_package as _core_module
import sys
sys.modules[__name__] = _core_module
```

`sys.modules` 교체 방식을 사용하는 이유: 테스트에서 `scoda_package._scoda_pkg = pkg`
같은 모듈 수준 상태 변경이 있으므로, 단순 re-export로는 상태 불일치가 발생한다.
`sys.modules` 교체로 두 import 경로가 동일한 모듈 객체를 가리키게 한다.

---

## 4. Import 규칙

```python
# Core 라이브러리 (새로운 표준 방식)
from scoda_engine_core import ScodaPackage, get_db

# Desktop/Server 모듈에서 core 사용
from scoda_engine_core import get_db            # app.py
from scoda_engine_core import get_db, ensure_overlay_db, get_mcp_tools  # mcp_server.py
import scoda_engine_core as scoda_package       # gui.py (속성 접근 패턴 유지)
from scoda_engine_core import set_active_package  # serve.py
```

---

## 5. 구현 단계 (10 Steps)

### Step 1: `core/` 디렉토리 및 `core/pyproject.toml` 생성

신규 파일 생성. `dependencies = []` (순수 stdlib).

### Step 2: `core/scoda_engine_core/` 패키지 생성

- **2a.** `scoda_engine/scoda_package.py`를 `core/scoda_engine_core/scoda_package.py`로 복사 (원본 그대로)
- **2b.** `core/scoda_engine_core/__init__.py` 생성 (public API re-export)
- **2c.** 복사된 `scoda_package.py`에서 `base_dir` 계산 수정:

```python
# 기존 (scoda_engine/scoda_package.py — 2단계):
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 변경 (core/scoda_engine_core/scoda_package.py — 3단계):
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

`_resolve_paths()` (~line 571)와 `get_registry()` (~line 451) 두 곳에 적용.
이것이 `scoda_package.py`의 **유일한 내용 변경**.

### Step 3: 기존 `scoda_engine/scoda_package.py`를 shim으로 교체

789줄 파일을 4줄 `sys.modules` 교체 shim으로 대체. **중간 위험도** — 이후 모든 import에 영향.

### Step 4: `scoda_engine/` 패키지 파일 import 업데이트

| 파일 | 변경 |
|------|------|
| `app.py` | `from .scoda_package import ...` → `from scoda_engine_core import ...` |
| `mcp_server.py` | `from .scoda_package import ...` → `from scoda_engine_core import ...` |
| `gui.py` | `from . import scoda_package` → `import scoda_engine_core as scoda_package` + logger handler 추가 |
| `serve.py` | `from .scoda_package import ...` → `from scoda_engine_core import ...` |

### Step 5: root `pyproject.toml` 업데이트

- dependencies에 `"scoda-engine-core>=0.1.0"` 추가
- `[tool.setuptools.packages.find]`에 `exclude = ["core*"]` 추가

### Step 6: `scripts/release.py` import 업데이트

`from scoda_engine.scoda_package import ScodaPackage` → `from scoda_engine_core import ScodaPackage`

### Step 7: 테스트 import 업데이트

- **7a.** `conftest.py` — 3곳 import 변경
- **7b.** `test_runtime.py` — ~20곳 import 변경 (MCP 관련 mock은 그대로)
- **7c.** `test_mcp.py` — 변경 없음 (subprocess 기반)
- **7d.** `test_mcp_basic.py` — 변경 없음 (subprocess 기반)

### Step 8: `ScodaDesktop.spec` 업데이트

- `hiddenimports`에 `scoda_engine_core`, `scoda_engine_core.scoda_package` 추가
- `datas`에 `('core/scoda_engine_core', 'scoda_engine_core')` 추가

### Step 9: 문서 업데이트

`CLAUDE.md`, `README.md` — 새 구조, 새 import 규칙, 개발 환경 설정 반영.

### Step 10: 검증

```bash
pip install -e ./core
pip install -e ".[dev]"
pytest tests/
```

---

## 6. 실행 순서 요약

| Step | 대상 | 위험도 |
|------|------|--------|
| 1 | `core/pyproject.toml` 생성 | 없음 |
| 2a-b | `scoda_package.py` 복사 + `__init__.py` 생성 | 없음 |
| 2c | `base_dir` 수정 (2곳) | 낮음 |
| 3 | shim 교체 | **중간** |
| 4a-d | `scoda_engine/` import 변경 (4파일) | 낮음 |
| 5 | root `pyproject.toml` 변경 | 낮음 |
| 6 | `scripts/release.py` import 변경 | 낮음 |
| 7a-b | 테스트 import 변경 | 낮음 |
| 8 | `ScodaDesktop.spec` 변경 | 낮음 |
| 9 | 문서 업데이트 | 없음 |
| 10 | 재설치 + 테스트 실행 | 검증 |

**권장:** Step 1~2c 완료 후 즉시 `pip install -e ./core`, 이후 Step 3~7 일괄, `pytest` 검증, 마지막으로 Step 8~9.

---

## 7. 주의 사항

1. **모듈 수준 mutable state** — `sys.modules` 교체로 두 import 경로가 동일 객체를 공유해야 함
2. **Logger 이름 변경** — `scoda_engine.scoda_package` → `scoda_engine_core.scoda_package`. GUI의 log handler 업데이트 필요
3. **`base_dir` 계산** — `__file__` 기반 `dirname` 호출 횟수가 파일 위치 깊이에 의존. 이동 시 반드시 조정
4. **`conftest.py`의 `init_overlay_db` import** — 순수 sqlite3 모듈이므로 분리 영향 없음
