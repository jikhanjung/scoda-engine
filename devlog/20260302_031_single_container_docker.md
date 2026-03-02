# 031: nginx + app 단일 Docker 이미지

**Date:** 2026-03-02
**Status:** Done
**Related:** P22 (Production Web Viewer), 029, 030

## 개요

기존 2-컨테이너 구성(app + nginx)을 단일 컨테이너 `scoda-server`로 통합.
배포가 `docker run` 한 줄로 가능해지고, Docker Hub에 게시하여 어디서든 pull 가능.

## 변경 사항

### 1. `deploy/Dockerfile` 수정

- 런타임 이미지에 `nginx` 패키지 설치 (`apt-get install nginx`)
- nginx 설정, 에러 페이지, 정적 파일을 동일 이미지에 복사
- `entrypoint.sh`로 nginx + gunicorn 동시 실행
- 포트 80만 EXPOSE (gunicorn은 127.0.0.1:8000 내부 전용)
- CRLF 안전장치 (`sed -i 's/\r$//'`) 추가
- `USER scoda` 제거 — gunicorn이 자체적으로 privilege drop

### 2. `deploy/entrypoint.sh` (신규)

```sh
#!/bin/sh
nginx                    # 백그라운드 데몬
exec gunicorn -c gunicorn.conf.py 'scoda_engine.serve_web:create_app()'
```

gunicorn이 PID 1 → `docker stop` 시 SIGTERM 직접 수신.

### 3. `deploy/nginx/nginx.conf` 수정

- upstream: `app:8000` → `127.0.0.1:8000` (같은 컨테이너 내부 통신)

### 4. `deploy/gunicorn.conf.py` 수정

- bind: `0.0.0.0:8000` → `127.0.0.1:8000` (nginx만 외부 노출)
- `user = "scoda"`, `group = "scoda"` 추가 (privilege drop)
- `preload_app = False` — worker가 scoda 유저로 앱 로드 (root로 preload 시 temp 파일 권한 문제 해결)

### 5. `deploy/docker-compose.yml` 간소화

- nginx 서비스 제거, app 서비스만 유지
- `name: scoda-server` (Compose 프로젝트명)
- `image: scoda-server`, `container_name: scoda-server`
- 포트: `${SCODA_PUBLIC_PORT:-80}:80`
- `SCODA_PACKAGE` 환경변수 추가 (기본값 `trilobase-assertion`)
- healthcheck 포트 80으로 변경

### 6. `deploy/README.md` 수정

- 아키텍처 설명을 단일 컨테이너로 업데이트
- Docker Hub pull/run 방법 추가 (커스텀 포트 포함)
- 새 버전 푸시 방법 추가

### 7. `deploy/nginx/Dockerfile` 삭제

- 별도 nginx 컨테이너가 불필요해짐

### 8. `DEFAULT_PACKAGE` build arg 기본값 수정

- `${DEFAULT_PACKAGE:-}` → `${DEFAULT_PACKAGE:-trilobase-assertion}`
- 빈 문자열이 Dockerfile ARG 기본값을 덮어써서 paleocore가 선택되는 문제 수정

## 배포 확인

- **Docker Hub:** `honestjung/scoda-server:0.1.0` (+ `latest`)
- **GCP 서버:** http://34.64.158.160:8080/ 에서 정상 동작 확인
- 실행: `docker run -d -p 8080:80 --name scoda-server honestjung/scoda-server`

## 트러블슈팅

### CRLF 줄바꿈 문제
- **증상:** `exec /app/entrypoint.sh: no such file or directory`
- **원인:** Windows에서 생성된 entrypoint.sh의 CRLF 줄바꿈
- **해결:** Dockerfile에서 `sed -i 's/\r$//'` 실행하여 LF로 변환

### SQLite DB 접근 권한
- **증상:** `sqlite3.OperationalError: unable to open database file`
- **원인:** `preload_app = True`로 root가 temp 디렉토리를 생성 → scoda worker가 접근 불가
- **해결:** `preload_app = False`로 변경, 각 worker가 scoda 유저로 직접 앱 로드

## 파일 변경 요약

| 파일 | 작업 |
|------|------|
| `deploy/Dockerfile` | 수정 |
| `deploy/entrypoint.sh` | 신규 |
| `deploy/nginx/nginx.conf` | 수정 |
| `deploy/gunicorn.conf.py` | 수정 |
| `deploy/docker-compose.yml` | 수정 |
| `deploy/README.md` | 수정 |
| `deploy/nginx/Dockerfile` | 삭제 |

## Docker Hub

```bash
# 이미지: honestjung/scoda-server
# 초기 버전: 0.1.0

# 다른 서버에서 실행 (latest)
docker run -d -p 80:80 --name scoda-server honestjung/scoda-server

# 커스텀 포트
docker run -d -p 8080:80 --name scoda-server honestjung/scoda-server
```
