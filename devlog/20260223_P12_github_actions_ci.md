# P12 — GitHub Actions CI 테스트 자동화

**Date:** 2026-02-23

## 목표

PR 및 main push 시 pytest를 자동 실행하는 CI 파이프라인 구축.

## 구현 내용

### `.github/workflows/test.yml`

- **트리거:** `push` (main), `pull_request` (main)
- **OS 매트릭스:** ubuntu-latest, windows-latest
- **Python 매트릭스:** 3.10, 3.12
- **설치 순서:** `pip install -e ./core` → `pip install -e ".[dev]"`
- **테스트:** `pytest tests/ -v`
- `fail-fast: false` — 한 조합 실패 시에도 나머지 조합 계속 실행

### 설계 결정

1. **OS 매트릭스에 macOS 미포함:** 현재 macOS 사용자 없음, 비용 절감. 필요 시 추가 가능.
2. **릴리스 자동화 미포함:** 테스트 CI 안정화 후 별도 워크플로우로 추가 예정.
3. **캐시 미적용:** 의존성 규모가 작아 설치 시간이 짧으므로 초기에는 불필요.

## 수정 파일

| 파일 | 작업 |
|------|------|
| `.github/workflows/test.yml` | 신규 — CI 워크플로우 |
| `devlog/20260223_P12_github_actions_ci.md` | 신규 — 본 문서 |
| `docs/HANDOFF.md` | P12 완료 반영 |
