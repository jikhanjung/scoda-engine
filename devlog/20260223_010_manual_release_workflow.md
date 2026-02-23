# Manual Release 워크플로우 — 구현 완료

**Date:** 2026-02-23
**Type:** Implementation
**Plan:** `devlog/20260223_P13_manual_release_workflow.md`

---

## 변경 요약

GitHub Actions `workflow_dispatch` 기반 수동 릴리스 워크플로우 구축.
PyInstaller 빌드 → ZIP 아티팩트 → GitHub Release 생성까지의 전체 파이프라인.

### 변경 내용

| 변경 | 설명 |
|------|------|
| Release 워크플로우 생성 | `.github/workflows/release.yml` — workflow_dispatch 트리거 |
| 입력 파라미터 | `version_tag` (필수), `prerelease` (boolean), `release_notes` (선택) |
| build job | ubuntu/windows 매트릭스, Python 3.12, PyInstaller 빌드 |
| 아티팩트 패키징 | Linux: `zip -j`, Windows: `Compress-Archive` (pwsh) |
| release job | `softprops/action-gh-release@v2`로 GitHub Release 생성 |
| 태그 형식 | `{version_tag}-build.{run_number}` |

## 수정 파일

| 파일 | 변경 |
|------|------|
| `.github/workflows/release.yml` | **신규** — Manual Release 워크플로우 |
| `devlog/20260223_P13_manual_release_workflow.md` | **신규** — P13 계획 문서 |
| `docs/HANDOFF.md` | P13 완료 반영, Release workflow 문서 참조 추가 |

## 설계 결정

- **단일 워크플로우**: 빌드가 단순하므로 reusable workflow로 분리하지 않음
- **Python 3.12 고정**: 릴리스 빌드는 단일 버전, 다중 버전 테스트는 test.yml에서 커버
- **macOS 미포함**: 현재 사용자 없음, 필요 시 매트릭스에 추가만 하면 됨
- **`fail-fast: false`**: 한 OS 실패 시에도 나머지 빌드 계속 실행
- **retention-days: 5**: 릴리스 아티팩트는 GitHub Release에 보존되므로 CI artifact는 단기 보관
