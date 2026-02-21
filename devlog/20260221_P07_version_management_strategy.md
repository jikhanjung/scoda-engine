# P07: 버전 관리 전략 수립 및 구현

**작성일:** 2026-02-21

---

## 1. 개요

scoda-engine-core와 ScodaDesktop은 배포 채널(PyPI vs GitHub Releases)과 릴리스 주기가
다르므로 독립적인 SemVer 버전 관리가 필요하다. 이 문서는 두 패키지의 버전 관리 전략,
버전 소스 단일화, Git 태그 네이밍 규칙을 정의한다.

---

## 2. 독립 SemVer 전략

| 패키지 | 배포 채널 | 초기 버전 | 버전 소스 |
|--------|-----------|-----------|-----------|
| `scoda-engine-core` | PyPI | `0.1.0` | `core/pyproject.toml` + `core/scoda_engine_core/__init__.py` |
| `scoda-engine` (Desktop) | GitHub Releases / PyPI | `0.1.0` | `pyproject.toml` + `scoda_engine/__init__.py` |

두 패키지의 버전은 **독립적으로** 관리한다. Core의 버전 변경이 Desktop 버전 변경을
요구하지 않으며, 그 반대도 마찬가지이다.

---

## 3. 버전 소스 단일화 (Single Source of Truth)

### 3.1 원칙

각 패키지의 버전은 `pyproject.toml`의 `version` 필드가 정본(canonical)이다.
`__init__.py`의 `__version__` 변수는 런타임 접근을 위한 보조 소스로,
릴리스 시 `pyproject.toml`과 동기화해야 한다.

### 3.2 런타임 접근

```python
# Core
from scoda_engine_core import __version__
print(__version__)  # "0.1.0"

# Desktop
from scoda_engine import __version__
print(__version__)  # "0.1.0"
```

### 3.3 GUI 표시

GUI 타이틀바에 Desktop 버전을 표시한다:
```
SCODA Desktop v0.1.0
```

---

## 4. Git 태그 네이밍 규칙

두 패키지가 같은 repo에 있으므로 태그에 접두사를 사용하여 구분한다:

| 패키지 | 태그 형식 | 예시 |
|--------|-----------|------|
| `scoda-engine-core` | `core-v<MAJOR>.<MINOR>.<PATCH>` | `core-v0.1.0`, `core-v0.2.0` |
| `scoda-engine` (Desktop) | `desktop-v<MAJOR>.<MINOR>.<PATCH>` | `desktop-v0.1.0`, `desktop-v1.0.0` |

---

## 5. 버전 범프 규칙

SemVer 2.0.0 표준을 따른다:

| 변경 유형 | 범프 | 예시 |
|-----------|------|------|
| 하위 호환 버그 수정 | PATCH | `0.1.0` → `0.1.1` |
| 하위 호환 기능 추가 | MINOR | `0.1.0` → `0.2.0` |
| 하위 호환 깨짐 (breaking change) | MAJOR | `0.1.0` → `1.0.0` |

### 0.x 기간 규칙

`0.x.y` 동안은 MINOR 범프가 breaking change를 포함할 수 있다.
`1.0.0` 이후부터 SemVer를 엄격히 적용한다.

---

## 6. Desktop의 Core 의존성 범위

Desktop `pyproject.toml`에서 Core 의존성을 호환 범위로 지정한다:

```toml
"scoda-engine-core>=0.1.0,<1.0.0"
```

Core가 `1.0.0`에 도달하면 Desktop 의존성도 함께 업데이트한다.

---

## 7. 버전 범프 체크리스트

릴리스 시 다음 항목을 순서대로 확인한다:

### Core 릴리스
1. `core/pyproject.toml`의 `version` 업데이트
2. `core/scoda_engine_core/__init__.py`의 `__version__` 동기화
3. Git 태그: `core-v<VERSION>`
4. PyPI 배포

### Desktop 릴리스
1. `pyproject.toml`의 `version` 업데이트
2. `scoda_engine/__init__.py`의 `__version__` 동기화
3. Core 의존성 범위 확인 (필요시 업데이트)
4. Git 태그: `desktop-v<VERSION>`
5. GitHub Release + PyInstaller EXE 빌드

---

## 8. 구현 내역

| 변경 | 파일 |
|------|------|
| `__version__ = "0.1.0"` 추가 | `core/scoda_engine_core/__init__.py` |
| `__version__ = "0.1.0"` 추가 | `scoda_engine/__init__.py` |
| GUI 타이틀바에 버전 표시 | `scoda_engine/gui.py` |
| Core 의존성 호환 범위 명시 | `pyproject.toml` |
