# 035: Docker 빌드 SSL 우회 + 프로덕션 엔진 이름 표시

**Date:** 2026-03-06
**Status:** Done
**Related:** P22 (Production Web Viewer), 030, 031, 034

## 개요

Docker 프로덕션 배포 관련 두 가지 개선:
1. 기관 네트워크에서 Docker 빌드 실패 문제 해결 (Hub SSL 검증 비활성화)
2. 프로덕션 웹 뷰어에서 "Powered by SCODA Server" 표시 (엔진 이름 분리)

## 변경 사항

### 1. Docker 빌드 시 Hub SSL 검증 비활성화 (`a1df10c`)

기관 네트워크 등에서 SSL 인증서 검증 실패로 `fetch_packages.py` 실행이
실패하는 문제 대응. Dockerfile에서 빌드 타임에 `SCODA_HUB_SSL_VERIFY=0`
환경변수를 설정하여 Hub 패키지 다운로드 시 SSL 검증을 건너뜀.

| 파일 | 내용 |
|------|------|
| `deploy/Dockerfile` | `ENV SCODA_HUB_SSL_VERIFY=0` 추가 (fetch_packages.py 실행 전) |

기존 `hub_client.py`의 SSL fallback 메커니즘(`SCODA_HUB_SSL_VERIFY` 환경변수)을
그대로 활용. 런타임에는 영향 없음 (빌드 타임 전용).

### 2. 프로덕션 엔진 이름 표시 (`721b12f`)

데스크탑과 프로덕션 웹 뷰어의 엔진 이름을 구분하여 표시.

| 파일 | 내용 |
|------|------|
| `scoda_engine/app.py` | `SCODA_ENGINE_NAME` 환경변수 도입 (기본값 `SCODA Desktop`), `ManifestResponse`에 `engine_name` 필드 추가, `_fetch_manifest()`에서 반환 |
| `scoda_engine/serve_web.py` | `create_app()`에서 `SCODA_ENGINE_NAME=SCODA Server` 설정 |
| `scoda_engine/static/js/app.js` | navbar subtitle에 동적 엔진 이름 표시 (`Powered by {engineName} v{version}`) |

#### 동작

- **데스크탑** (`serve.py`): "Powered by SCODA Desktop v0.1.6"
- **프로덕션** (`serve_web.py`): "Powered by SCODA Server v0.1.6"

## 파일 변경 요약

| 파일 | 작업 | 커밋 |
|------|------|------|
| `deploy/Dockerfile` | 수정 | `a1df10c` |
| `scoda_engine/app.py` | 수정 | `721b12f` |
| `scoda_engine/serve_web.py` | 수정 | `721b12f` |
| `scoda_engine/static/js/app.js` | 수정 | `721b12f` |
