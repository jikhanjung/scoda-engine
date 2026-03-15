# 038 — Navbar / Landing 엔진 버전 표시 + v0.3.3

**Date:** 2026-03-15

## 개요

헤더 navbar 우측과 랜딩 페이지에 엔진 이름·버전을 표시하도록 개선.
"Powered by scoda-server v0.3.3" 형태로 작은 폰트로 눈에 띄지 않게 노출.

## 변경 내용

### 1. Viewer navbar 우측 엔진 정보 (`index.html` + `app.js`)

- `index.html`: navbar 우측에 `<span id="navbar-engine-info">` 추가
  - 스타일: `text-white-50`, `font-size: 0.65em`, `white-space: nowrap`
  - Hub Refresh 버튼과 함께 `d-flex` 컨테이너로 묶음
- `app.js`: manifest 로드 후 `data.engine_name` + `data.engine_version` 으로 채움
  - "Powered by {engine_name} v{engine_version}" 형식

### 2. Landing 페이지 엔진 정보 (`landing.html` + `app.py`)

- `landing.html`: 우측 하단 고정 위치에 `<div class="engine-info">` 추가
  - 스타일: `position: fixed; bottom: 1rem; right: 1rem; color: #484f58; font-size: 0.7rem`
- JS: `/api/packages`와 `/healthz`를 `Promise.all`로 병렬 fetch 후 엔진 정보 표시
- `app.py`: `/healthz` 응답에 `engine_name` 필드 추가

### 3. v0.3.3 버전 업

- `pyproject.toml`, `scoda_engine/__init__.py`, `deploy/docker-compose.yml`: 0.3.2 → 0.3.3

## 표시 예시

| 환경 | 표시 |
|------|------|
| Docker (scoda-server) | Powered by scoda-server v0.3.3 |
| Desktop | Powered by SCODA Desktop v0.3.3 |
