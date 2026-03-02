# 030: Docker 빌드 시 Hub 패키지 자동 다운로드

**Date:** 2026-03-02
**Status:** Done
**Related:** P22 (Production Web Viewer)

## 개요

Docker 이미지 빌드 시 Hub에서 최신 `.scoda` 패키지를 자동으로 다운로드하여
이미지에 포함시키도록 변경. 기존에는 사용자가 `.scoda` 파일을 직접 준비하여
빌드 컨텍스트에 배치해야 했으나, 이제 빌드만 하면 모든 Hub 패키지가 자동 포함됨.

## 변경 사항

### 1. `deploy/fetch_packages.py` (신규)

Hub에서 최신 `.scoda` 패키지를 모두 다운로드하는 빌드 타임 스크립트.

- `scoda_engine_core.hub_client`의 기존 함수 재사용:
  - `fetch_hub_index()` → Hub index 가져오기
  - `download_package()` → 개별 패키지 다운로드 (SHA-256 검증 포함)
- Hub index의 모든 패키지에 대해 `latest` 버전 다운로드
- `--dest` 인자로 다운로드 디렉토리 지정 (기본 `/data/`)
- `--hub-url`, `--timeout` 옵션 지원
- 다운로드 결과 요약 출력 (패키지명, 버전, 크기)
- 다운로드 실패 시 exit code 1

### 2. `deploy/Dockerfile` 수정

```dockerfile
# 변경 전
ARG SCODA_FILE=data/package.scoda
COPY ${SCODA_FILE} /data/package.scoda

# 변경 후
COPY deploy/fetch_packages.py /tmp/fetch_packages.py
RUN mkdir -p /data && python /tmp/fetch_packages.py --dest /data/ && \
    chown -R scoda:scoda /data && rm /tmp/fetch_packages.py

ARG DEFAULT_PACKAGE=trilobase-assertion
ENV SCODA_PATH=/data/ \
    SCODA_PACKAGE=${DEFAULT_PACKAGE}
```

- 빌드 시 Hub에서 자동 다운로드 (네트워크 접근 필요)
- `DEFAULT_PACKAGE` build arg로 기본 서빙 패키지 지정 (이미지에 구워짐)
- 런타임에 `SCODA_PACKAGE` 환경변수로 override 가능

### 3. `scoda_engine/serve_web.py` 수정

`create_app()`에서 `SCODA_PATH`가 디렉토리인 경우 지원:

- **파일** → 기존대로 `register_scoda_path(path)` 호출
- **디렉토리** → `PackageRegistry.scan(path)` 호출 후 `SCODA_PACKAGE` 환경변수로 활성 패키지 선택. 미지정 시 첫 번째 패키지 자동 선택.
- `SCODA_PACKAGE` 환경변수 문서화

### 4. `deploy/docker-compose.yml` 수정

- `SCODA_FILE` build arg 제거
- `DEFAULT_PACKAGE` build arg 추가
- `SCODA_PATH=/data/` (디렉토리)

### 5. `deploy/.env.example` 수정

- `SCODA_FILE` → `DEFAULT_PACKAGE=trilobase-assertion`

### 6. `deploy/README.md` 수정

- 자동 다운로드 워크플로우 반영
- Build-time / Runtime 설정 테이블 분리
- 수동 `.scoda` 배치 단계 제거

## 파일 변경 요약

| 파일 | 작업 |
|------|------|
| `deploy/fetch_packages.py` | 신규 |
| `deploy/Dockerfile` | 수정 |
| `scoda_engine/serve_web.py` | 수정 |
| `deploy/docker-compose.yml` | 수정 |
| `deploy/.env.example` | 수정 |
| `deploy/README.md` | 수정 |

## 사용법

```bash
# 이미지 빌드 (Hub에서 자동 다운로드, 기본 패키지: trilobase-assertion)
cd deploy && docker compose up --build -d

# 다른 기본 패키지로 빌드
DEFAULT_PACKAGE=other-pkg docker compose build

# 런타임에 패키지 변경 (재빌드 불필요)
SCODA_PACKAGE=other-pkg docker compose up -d
```

## 테스트

- 기존 303개 테스트 전부 통과
- `fetch_packages.py` 구문 검증 완료
