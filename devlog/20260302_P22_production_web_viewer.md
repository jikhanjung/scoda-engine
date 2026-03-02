# P22: SCODA Engine 프로덕션 웹 뷰어 서비스

**Date:** 2026-03-02

## Context

현재 SCODA Engine의 웹 서버(`serve.py`)는 데스크탑용으로 설계되어 있다:
`127.0.0.1` 바인딩, 브라우저 자동 실행, 단일 uvicorn 워커.
`.scoda` 패키지를 브라우저만으로 열람하고 싶은 사용자를 위해
**읽기 전용 프로덕션 웹 뷰어** 배포 환경을 추가한다.

핵심 원칙: 기존 FastAPI 앱(`app.py`)을 그대로 재사용하고,
프로덕션 배포 레이어(Docker Compose + nginx + gunicorn)를 씌운다.

## 사용자 결정 사항

- **읽기 전용** — annotation/CRUD 없음, viewer 모드 강제
- **Docker Compose** — nginx(리버스 프록시) + gunicorn/uvicorn(앱)
- **단일 패키지** — 멀티패키지는 별도 설계 후 추가

## 아키텍처

```
Internet → :80 → nginx (정적 파일, gzip, 프록시)
                    → :8000 → gunicorn + uvicorn workers
                               SCODA_MODE=viewer
                               .scoda 볼륨 마운트
```

## 구현 계획

### 1. `scoda_engine/serve_web.py` (신규)

프로덕션 웹 서비스 진입점.

- `create_app()` 팩토리 함수 — gunicorn이 호출
  - `SCODA_MODE=viewer` 강제
  - `SCODA_DISABLE_MCP=1` 설정
  - `SCODA_PATH` 환경변수에서 `.scoda` 경로 읽기
  - `register_scoda_path()` 호출 후 `app` 반환
- `main()` CLI 진입점 — `python -m scoda_engine.serve_web`로 직접 실행 가능
  - `0.0.0.0` 바인딩, 브라우저 자동 열기 없음
  - 환경변수: `SCODA_PORT`(기본 8000), `SCODA_WORKERS`, `SCODA_LOG_LEVEL`

### 2. `scoda_engine/app.py` 수정 (최소 변경)

**변경 1**: `/healthz` 헬스체크 엔드포인트 추가 (~15줄, MCP mount 직전)
- `get_db()` → `SELECT 1` 실행하여 DB 연결 확인
- 반환: `{"status": "ok", "engine_version": "...", "mode": "..."}`
- 실패 시 503 반환

**변경 2**: MCP mount 조건부 처리 (1022-1024행)
- `SCODA_DISABLE_MCP=1`이면 MCP SSE 서버 마운트 건너뜀
- 데스크탑에서는 기존 동작 유지(기본값=MCP 활성)

### 3. `pyproject.toml` 수정

- `[project.optional-dependencies]`에 `web = ["gunicorn>=21.0"]` 추가
- `[project.scripts]`에 `scoda-web = "scoda_engine.serve_web:main"` 추가

### 4. `deploy/Dockerfile` (신규)

- 멀티스테이지 빌드: `python:3.12-slim`
- builder 단계: core + engine + gunicorn 설치
- runtime 단계: non-root `scoda` 유저, `/data/` 마운트 포인트
- 환경변수 기본값: `SCODA_MODE=viewer`, `SCODA_DISABLE_MCP=1`
- HEALTHCHECK: urllib로 `/healthz` 폴링
- CMD: `gunicorn -c gunicorn.conf.py 'scoda_engine.serve_web:create_app()'`

### 5. `deploy/gunicorn.conf.py` (신규)

- `worker_class = "uvicorn.workers.UvicornWorker"`
- `workers` = `SCODA_WORKERS` 환경변수 (기본 2)
- `bind = "0.0.0.0:8000"`
- `preload_app = True` (`.scoda` 1회 로드 후 fork)
- `timeout = 120`, `accesslog = "-"` (stdout)

### 6. `deploy/nginx/nginx.conf` (신규)

- upstream: `app:8000`
- `/static/` → nginx 직접 서빙 (7일 캐시, access_log off)
- `/healthz` → proxy pass (access_log off)
- `/mcp` → 404 차단 (방어)
- `/` → proxy pass (X-Real-IP, X-Forwarded-For 헤더)
- gzip 활성, 보안 헤더 (X-Content-Type-Options, X-Frame-Options)
- HTTPS 설정은 주석으로 문서화

### 7. `deploy/nginx/Dockerfile` (신규)

- `nginx:1.25-alpine` 기반
- `scoda_engine/static/`을 nginx html 디렉토리에 복사

### 8. `deploy/docker-compose.yml` (신규)

- **app** 서비스: deploy/Dockerfile, `.scoda` 볼륨 마운트(`:ro`), healthcheck
- **nginx** 서비스: deploy/nginx/Dockerfile, `${SCODA_PUBLIC_PORT:-80}:80`
- nginx는 `app` 서비스 healthy 후 시작 (`depends_on.condition`)
- 환경변수: `.env` 파일로 관리

### 9. 기타 신규 파일

- `deploy/nginx/50x.html` — nginx 에러 페이지
- `deploy/.env.example` — 환경변수 템플릿
- `.dockerignore` — 빌드 컨텍스트 제외
- `deploy/README.md` — 배포 가이드

## 파일 변경 요약

| 파일 | 작업 | 비고 |
|------|------|------|
| `scoda_engine/serve_web.py` | 신규 | 프로덕션 진입점 |
| `scoda_engine/app.py` | 수정 | +`/healthz`, MCP 조건부 mount |
| `pyproject.toml` | 수정 | +`web` extras, +`scoda-web` script |
| `deploy/Dockerfile` | 신규 | 멀티스테이지 빌드 |
| `deploy/gunicorn.conf.py` | 신규 | gunicorn 설정 |
| `deploy/nginx/nginx.conf` | 신규 | 리버스 프록시 |
| `deploy/nginx/Dockerfile` | 신규 | 정적 파일 포함 nginx |
| `deploy/nginx/50x.html` | 신규 | 에러 페이지 |
| `deploy/docker-compose.yml` | 신규 | 오케스트레이션 |
| `deploy/.env.example` | 신규 | 환경변수 템플릿 |
| `.dockerignore` | 신규 | 빌드 컨텍스트 제외 |
| `deploy/README.md` | 신규 | 배포 가이드 |

## 검증 방법

**1단계: 로컬 테스트 (Docker 없이)**
```bash
pip install -e ".[web]"
SCODA_PATH=/path/to/test.scoda python -m scoda_engine.serve_web
curl http://localhost:8000/healthz     # → {"status":"ok",...}
curl http://localhost:8000/api/manifest # → manifest JSON
curl -X POST http://localhost:8000/api/entities/species  # → 403
```

**2단계: 기존 테스트 통과 확인**
```bash
pytest tests/  # 303개 테스트 전부 통과
```

**3단계: Docker 테스트**
```bash
cd deploy
cp .env.example .env
mkdir -p data && cp /path/to/test.scoda data/package.scoda
docker compose up --build
curl http://localhost/healthz
curl http://localhost/static/css/style.css  # nginx 직접 서빙
curl http://localhost/api/manifest
curl http://localhost/mcp  # → 404
```
