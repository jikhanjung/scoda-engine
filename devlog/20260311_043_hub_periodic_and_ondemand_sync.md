# 043 — Hub 주기적 동기화 + 온디맨드 API

**Date:** 2026-03-11
**Scope:** `scoda_engine/serve_web.py`, `deploy/Dockerfile`

## 배경

Docker 컨테이너 환경에서 Hub 패키지 동기화가 빌드 시점 + 시작 시점에만 가능했음.
컨테이너를 재시작하지 않고도 Hub 변경 사항을 반영할 수 있는 메커니즘 필요.

## 변경 사항

### 1. 온디맨드 동기화 API (`POST /api/hub/sync`)

- `serve_web.py`의 `create_app()`에서 엔드포인트 등록
- SCODA_PATH가 디렉토리인 경우에만 활성화
- 응답: `{"status": "ok", "synced": <count>}`
- 사용: `curl -X POST http://localhost:8081/api/hub/sync`

### 2. 주기적 백그라운드 동기화 (`SCODA_HUB_SYNC_INTERVAL`)

- `threading.Timer` 기반 daemon 스레드로 주기적 Hub 체크
- 환경변수 `SCODA_HUB_SYNC_INTERVAL` (초 단위, 기본 0 = 비활성화)
- 86400 = 하루에 한 번
- 컨테이너 종료 시 daemon 스레드 자동 정리

### 3. Dockerfile 기본값 변경

- `SCODA_HUB_SYNC=1` — 시작 시 Hub 체크 활성화
- `SCODA_HUB_SYNC_INTERVAL=86400` — 24시간 주기 동기화

### 4. `_sync_hub_packages()` 반환값 추가

- 동기화된 패키지 수를 `int`로 반환 (API 응답에 사용)
- 기존 early return 경로에도 `return 0` 추가

## 환경변수 요약

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `SCODA_HUB_SYNC` | `0` | 시작 시 Hub 동기화 (`1`=활성) |
| `SCODA_HUB_SYNC_INTERVAL` | `0` | 주기적 동기화 간격 (초, `0`=비활성) |

## 테스트

- 기존 303개 테스트 모두 통과
