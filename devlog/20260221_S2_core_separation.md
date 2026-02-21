# S-2: scoda-engine-core 분리 구현

**작성일:** 2026-02-21

---

## 개요

`scoda_package.py`(789줄)를 `scoda-engine-core` 독립 패키지로 분리.
P06 계획서(`devlog/20260221_P06_core_separation_plan.md`)의 10단계를 실행.

## 변경 사항

### 신규 생성

| 파일 | 설명 |
|------|------|
| `core/pyproject.toml` | `scoda-engine-core` 패키지 설정, `dependencies = []` |
| `core/scoda_engine_core/__init__.py` | Public API re-export |
| `core/scoda_engine_core/scoda_package.py` | 원본 복사 + `base_dir` dirname 3단계로 수정 |

### Shim 교체

- `scoda_engine/scoda_package.py`: 789줄 → 7줄 `sys.modules` 교체 shim
- 기존 `from scoda_engine.scoda_package import ...` 호환 유지

### Import 마이그레이션

| 파일 | 변경 |
|------|------|
| `scoda_engine/app.py` | `from .scoda_package import` → `from scoda_engine_core import` |
| `scoda_engine/mcp_server.py` | 동일 |
| `scoda_engine/gui.py` | `from . import scoda_package` → `import scoda_engine_core as scoda_package` + logger handler 추가 |
| `scoda_engine/serve.py` | 동일 |
| `scripts/release.py` | `from scoda_engine.scoda_package import` → `from scoda_engine_core import` |
| `tests/conftest.py` | `import scoda_engine.scoda_package as` → `import scoda_engine_core as` |
| `tests/test_runtime.py` | 동일 + 내부 변수 접근 시 `scoda_engine_core.scoda_package` 직접 import |

### 설정 변경

- `pyproject.toml`: `scoda-engine-core>=0.1.0` 의존성 추가, `exclude = ["core*"]`
- `ScodaDesktop.spec`: 양쪽 exe에 `scoda_engine_core` hiddenimports + datas 추가

### 문서 업데이트

- `CLAUDE.md`: 구조도, import convention, 설치 명령 반영
- `README.md`: 프로젝트 구조, 설치 명령 반영
- `docs/HANDOFF.md`: S-2 완료 기록, next steps 업데이트, 패키지 레이아웃 반영

## 테스트 결과

```
196 passed in 58.82s
```

모든 테스트 통과 (runtime + MCP subprocess).

## PyInstaller 빌드 수정 (ScodaDesktop.spec)

Windows에서 exe 빌드 후 실행 시 여러 문제가 발생하여 순차적으로 수정.
**근본 원인**: conda/pip 환경이 제대로 세팅되지 않은 상태에서 빌드하여
PyInstaller가 의존성을 찾지 못한 것이 핵심 문제였음.

### 수정 이력

| 문제 | 원인 | 수정 |
|------|------|------|
| `No module named 'glob'` | `datas`로 .py 복사 시 import 의존성 미추적 | `datas`에서 `scoda_engine_core` 제거 |
| `No module named 'scoda_engine_core'` | editable install의 `.pth`를 PyInstaller가 못 따라감 | `pathex=['core']` 추가 |
| `No module named 'uvicorn'` | 빌드 환경 pip 미설치 + PyInstaller 수집 불충분 | `collect_all('uvicorn')` + 환경 재설치 |

### 최종 ScodaDesktop.spec 핵심 변경

```python
from PyInstaller.utils.hooks import collect_all
_uvi_datas, _uvi_binaries, _uvi_hidden = collect_all('uvicorn')

a = Analysis(
    pathex=['core'],                    # scoda_engine_core 소스 경로
    binaries=[] + _uvi_binaries,
    datas=[...] + _uvi_datas,
    hiddenimports=[..., 'uvicorn'] + _uvi_hidden,
)
```

### 빌드 전 필수 사항

```bash
pip install -e ./core
pip install -e ".[dev]"
```

빌드 환경에서 반드시 위 명령을 먼저 실행해야 PyInstaller가 모든 의존성을 수집할 수 있음.

## 주의사항

1. 테스트에서 모듈 내부 변수(`_registry`, `_scoda_pkg` 등) 접근 시
   `import scoda_engine_core.scoda_package as sp_mod` 필요
   (`__init__.py`는 private 변수를 re-export하지 않음)
2. GUI logger: `scoda_engine_core` 네임스페이스 handler 추가됨
3. `base_dir` 계산: core 위치에서 dirname 3회 (`core/scoda_engine_core/scoda_package.py` → project root)
