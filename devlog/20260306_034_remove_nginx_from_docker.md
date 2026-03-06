# 034: Docker에서 nginx 제거 — gunicorn 직접 서빙

**Date:** 2026-03-06

## 변경 사항

Docker 이미지에서 nginx 리버스 프록시를 제거하고 gunicorn(uvicorn worker)이
포트 8081에서 직접 서빙하도록 단순화.

### 변경 파일

| 파일 | 내용 |
|------|------|
| `deploy/Dockerfile` | nginx 설치/설정 제거, `CMD`로 gunicorn 직접 실행, 포트 8081 |
| `deploy/gunicorn.conf.py` | 바인딩 `0.0.0.0:8081` (기존 `127.0.0.1:8000`) |
| `deploy/docker-compose.yml` | 포트 매핑 `8081:8081`, 헬스체크 포트 변경 |

### 삭제 파일

| 파일 | 이유 |
|------|------|
| `deploy/entrypoint.sh` | nginx 시작 로직 포함 — 불필요 |
| `deploy/nginx/nginx.conf` | nginx 설정 — 불필요 |
| `deploy/nginx/50x.html` | nginx 에러 페이지 — 불필요 |

## 이유

- 단일 컨테이너 내 nginx + gunicorn 구성의 복잡성 제거
- 개발/배포 환경 단순화
- 필요 시 외부 리버스 프록시(nginx, Caddy 등)를 별도 컨테이너로 구성 가능
