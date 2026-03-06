# 037: Release workflow에 Docker Hub 빌드·push 추가

**Date:** 2026-03-06
**Status:** Done
**Related:** 034, 035 (Docker 관련)

## 개요

Manual Release GitHub Actions workflow에 Docker Hub 이미지 빌드·push 단계 추가.
기존 Desktop 빌드(PyInstaller)와 병렬로 실행되며, 모두 완료된 후 GitHub Release 생성.

## 변경 사항

- `.github/workflows/release.yml`: `docker` job 추가
  - `docker/setup-buildx-action`, `docker/login-action`, `docker/build-push-action` 사용
  - `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` secrets 필요
  - 버전 태그에서 `v` prefix 제거 (예: `v0.1.8` → `0.1.8`)
  - 태그: `honestjung/scoda-server:<version>` + `honestjung/scoda-server:latest`
- `release` job이 `build`와 `docker` 모두 완료 후 실행되도록 변경
- Release notes에 Docker pull 명령어 포함
- Desktop 버전 0.1.7 → 0.1.8
