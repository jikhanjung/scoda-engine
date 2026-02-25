# 018 — Navbar subtitle: "Powered by SCODA Desktop v{version}"

**Date:** 2025-02-25

## 배경

웹 뷰어에서 패키지 이름/버전 아래에 "SCODA Desktop"이라고 하드코딩되어 있었음.
엔진 버전을 동적으로 표시하고 "Powered by" 문구를 추가하고자 함.

## 변경 내용

### `scoda_engine/app.py`
- `ENGINE_VERSION` import 추가 (`scoda_engine.__version__`)
- `ManifestResponse` 모델에 `engine_version: str` 필드 추가
- `_fetch_manifest()` 두 return 경로 모두에 `engine_version` 포함

### `scoda_engine/static/js/app.js`
- subtitle을 `"Powered by SCODA Desktop v{engine_version}"` 형태로 동적 표시
- `engine_version`이 없을 경우 버전 없이 fallback

## 결과

- `/api/manifest` 응답에 `engine_version` 필드가 포함됨
- 웹 UI navbar subtitle: `Powered by SCODA Desktop v0.1.2`
- 버전 업데이트 시 `scoda_engine/__init__.py`의 `__version__`만 수정하면 자동 반영
- 기존 223 tests 전체 통과
