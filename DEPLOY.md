# scoda-server 운영 배포 (dolfinid)

일반 Docker 사용법은 `deploy/README.md`. 이 문서는 운영 호스트의 레이아웃과 운영 변경 기록이다.

## 레이아웃

- 호스트: **dolfinid** (GCP, 외부 IP 34.64.158.160). 컨테이너 `scoda-server`.
- 디렉토리: `/srv/scoda-server/`
  - `docker-compose.yml`: 운영 compose. 저장소 `deploy/docker-compose.yml` 과 같은 꼴이지만, 이미지는 `honestjung/scoda-server:${IMAGE_TAG}` 이고 `build:` 가 없다.
  - `.env`: `IMAGE_TAG` (deploy.sh 가 바꿈) · `SCODA_PUBLIC_PORT=127.0.0.1:8081`.
  - `deploy.sh <버전>`: `.env` 의 `IMAGE_TAG` 를 바꾸고 `docker compose pull` → `down` → `up -d`. 저장소에는 없고 서버에만 있다.
- 데이터: named volume `scoda-data` → `/data` (Hub 패키지, `SCODA_HUB_SYNC=1`).
- 앞단: 호스트 nginx `/etc/nginx/sites-enabled/scoda-server` 가 **:8080** 에서 받아 `127.0.0.1:8081` 로 프록시한다 (`/mcp` 포함).
- 이미지: GitHub Actions `release.yml` 이 `honestjung/scoda-server:<버전>` 과 `:latest` 를 Docker Hub 에 올린다.

## 배포

```bash
ssh dolfinid '/srv/scoda-server/deploy.sh 0.3.9'
ssh dolfinid 'docker ps --filter name=scoda-server --format "{{.Image}} {{.Ports}} {{.Status}}"'
```

⚠️ **deploy.sh 는 compose 파일을 덮어쓰지 않는다.** 저장소의 `deploy/docker-compose.yml` 을 고쳐도 운영에는 들어가지 않으므로, 운영 compose 는 손으로 맞춘다.

## 운영 변경 기록 (append-only)

- **2026-11-06 포트 바인딩 127.0.0.1 로**
  - 컨테이너가 `0.0.0.0:8081` 로 열려 있어, nginx(:8080) 를 거치지 않고 외부 IP 의 :8081 로 바로 들어올 수 있었다.
  - 운영 `.env` 에 `SCODA_PUBLIC_PORT=127.0.0.1:8081` 을 넣었다. 그 전 `.env` 는 남기지 않았다.
  - 저장소 `deploy/docker-compose.yml` 기본값을 `${SCODA_PUBLIC_PORT:-127.0.0.1:8081}` 로 바꾸고 `.env.example` · README 를 맞췄다 (d917ec4). 모든 인터페이스에 열려면 `SCODA_PUBLIC_PORT=8081`.
  - 운영 compose 의 기본값도 같게 맞췄다. 백업은 `docker-compose.yml.bak-20261106`. 렌더 결과가 같아 컨테이너는 재시작되지 않았다. `.env` 줄이 빠져도 127.0.0.1 로 열린다.
  - Portainer 는 10-24 에 지웠다. 남아 있던 `portainer-stack.yml` · `portainer-stack.yml.bak-20261023` 과 빈 `test.txt` 를 지웠다.
  - 버전은 0.3.9 그대로 (코드 변경 없음, 새 판 안 냄).
  - 확인: `ss -ltn | grep :8081` → `127.0.0.1:8081` 만, 외부 IP 에서 :8081 닫힘, 컨테이너 healthy.
  - 같은 날 같은 이유로 fcmanager 도 바꿨다 (0.6.28, `BIND_ADDR`).
