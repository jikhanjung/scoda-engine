# P22: 프로덕션 웹 뷰어 Docker 배포 구현

**Date:** 2026-03-02

## 요약

`.scoda` 패키지를 읽기 전용으로 웹 서비스하기 위한 프로덕션 배포 환경 구현.
기존 FastAPI 앱(`app.py`)을 그대로 재사용하고, Docker Compose + nginx + gunicorn 레이어를 추가.

## 아키텍처

```
Internet → :80 → nginx (정적 파일, gzip, 리버스 프록시)
                    → :8000 → gunicorn + uvicorn workers
                               SCODA_MODE=viewer (읽기 전용)
                               .scoda 볼륨 마운트
```

## 구현 내용

### 1. `scoda_engine/serve_web.py` (신규)

프로덕션 웹 서비스 진입점.

- `create_app()` — gunicorn용 팩토리 함수. `SCODA_MODE=viewer` 강제, `SCODA_PATH`에서 `.scoda` 경로 읽어 `register_scoda_path()` 호출 후 `app` 반환.
- `main()` — CLI 진입점 (`python -m scoda_engine.serve_web`). `0.0.0.0` 바인딩, 브라우저 자동 열기 없음. `--scoda-path`, `--port`, `--workers`, `--log-level` 인자 지원. 환경변수(`SCODA_PORT`, `SCODA_WORKERS`, `SCODA_LOG_LEVEL`)도 사용 가능.

### 2. `scoda_engine/app.py` 수정

**`/healthz` 엔드포인트 추가**: `get_db()` → `SELECT 1`로 DB 연결 확인. 정상 시 `{"status":"ok", "engine_version":"...", "mode":"..."}`, 실패 시 503 반환.

**MCP mount opt-in 전환**: `SCODA_DISABLE_MCP` 방식에서 `SCODA_ENABLE_MCP=1` opt-in으로 변경. MCP는 기본적으로 비활성이며, 데스크탑 `serve.py`에서만 명시적으로 활성화.

```python
# 변경 전
from .mcp_server import create_mcp_app
app.mount("/mcp", create_mcp_app())

# 변경 후
if os.environ.get('SCODA_ENABLE_MCP') == '1':
    from .mcp_server import create_mcp_app
    app.mount("/mcp", create_mcp_app())
```

### 3. `scoda_engine/serve.py` 수정

app import 전에 `os.environ.setdefault('SCODA_ENABLE_MCP', '1')` 추가하여 데스크탑 모드에서 MCP 활성 유지.

### 4. `pyproject.toml` 수정

- `[project.optional-dependencies]`에 `web = ["gunicorn>=21.0"]` 추가
- `[project.scripts]`에 `scoda-web = "scoda_engine.serve_web:main"` 추가

### 5. `deploy/` 디렉토리 (전체 신규)

| 파일 | 내용 |
|------|------|
| `Dockerfile` | 멀티스테이지 빌드 (python:3.12-slim), non-root `scoda` 유저, `/data/` 마운트, urllib HEALTHCHECK |
| `gunicorn.conf.py` | UvicornWorker, `preload_app=True`, 환경변수 기반 workers/bind/loglevel |
| `nginx/nginx.conf` | upstream `app:8000`, `/static/` 직접 서빙 (7일 캐시), `/mcp` 404 차단, gzip, 보안 헤더, HTTPS 주석 문서화 |
| `nginx/Dockerfile` | nginx:1.25-alpine, static 파일 + 50x.html 포함 |
| `nginx/50x.html` | 앱 미응답 시 에러 페이지 |
| `docker-compose.yml` | app + nginx 2-서비스. `.scoda` 읽기전용 볼륨, healthcheck 기반 의존성 |
| `.env.example` | `SCODA_FILE`, `SCODA_PUBLIC_PORT`, `SCODA_WORKERS`, `SCODA_LOG_LEVEL` |
| `README.md` | Quick Start, 설정 변수 표, 아키텍처, HTTPS 가이드 |

### 6. `.dockerignore` (프로젝트 루트, 신규)

`.git/`, `docs/`, `design/`, `devlog/`, `*.scoda`, `*.db`, `tests/`, 데스크탑 전용 파일 등 빌드 컨텍스트에서 제외.

### 7. `tests/conftest.py` 수정

app import 전 `os.environ.setdefault('SCODA_ENABLE_MCP', '1')` 추가. MCP opt-in 전환으로 인해 테스트에서 MCP mount가 필요하므로 명시적 활성화.

## 설계 결정

### MCP opt-in (SCODA_ENABLE_MCP)

초기 계획은 `SCODA_DISABLE_MCP=1`로 프로덕션에서만 비활성화하는 방식이었으나, 구현 후 MCP를 기본 비활성으로 전환. `SCODA_ENABLE_MCP=1` opt-in 방식이 보안 측면에서 더 안전하고, 프로덕션 배포 설정이 단순해짐.

영향: `serve.py` (데스크탑)에서만 명시적 활성화, `conftest.py`에서 테스트용 활성화 추가.

## 검증

- 303개 기존 테스트 전부 통과
- `serve_web` 모듈 import 정상 확인
- `/healthz` 엔드포인트 라우트 등록 확인
- MCP 조건부 mount 동작 확인 (활성/비활성 양쪽)

## 파일 변경 요약

| 파일 | 작업 |
|------|------|
| `scoda_engine/serve_web.py` | 신규 |
| `scoda_engine/app.py` | 수정 |
| `scoda_engine/serve.py` | 수정 |
| `pyproject.toml` | 수정 |
| `deploy/Dockerfile` | 신규 |
| `deploy/gunicorn.conf.py` | 신규 |
| `deploy/nginx/nginx.conf` | 신규 |
| `deploy/nginx/Dockerfile` | 신규 |
| `deploy/nginx/50x.html` | 신규 |
| `deploy/docker-compose.yml` | 신규 |
| `deploy/.env.example` | 신규 |
| `deploy/README.md` | 신규 |
| `.dockerignore` | 신규 |
| `tests/conftest.py` | 수정 |
| `HANDOFF.md` | 수정 |
