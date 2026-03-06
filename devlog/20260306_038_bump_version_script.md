# 038: 버전 업데이트 스크립트 추가

**Date:** 2026-03-06
**Status:** Done
**Related:** 036, 037

## 배경

버전을 올릴 때 `pyproject.toml`만 수정하고 `scoda_engine/__init__.py`의
`__version__`을 빠뜨리는 실수가 발생. 웹 UI의 "Powered by SCODA Server v0.1.x"
표시가 실제 릴리즈 버전과 불일치하는 문제로 이어짐.

## 변경 사항

- `scripts/bump_version.py` 추가
  - `pyproject.toml`의 `version`과 `scoda_engine/__init__.py`의 `__version__`을
    한 번에 업데이트
  - `v` prefix 자동 제거 (`v0.1.9` → `0.1.9`)
  - 사용법: `python scripts/bump_version.py 0.1.9`
