# P13 — Manual Release 워크플로우

**Date:** 2026-02-23

## 목표

GitHub Actions `workflow_dispatch`를 통한 수동 릴리스 워크플로우 구축.
P12에서 테스트 CI를 완성했으므로, 릴리스 빌드 자동화를 추가한다.

## 구현 내용

### `.github/workflows/release.yml`

- **트리거:** `workflow_dispatch` (수동 실행)
- **입력 파라미터:**
  - `version_tag` — 버전 태그 (예: `v0.2.0`)
  - `prerelease` — 프리릴리스 여부 (boolean, 기본 false)
  - `release_notes` — 릴리스 노트 (markdown, 선택)
- **build job:**
  - OS 매트릭스: ubuntu-latest, windows-latest
  - Python 3.12 고정 (릴리스 빌드용)
  - `pip install -e ./core && pip install -e ".[dev]" && pip install pyinstaller`
  - `python scripts/build.py --clean`으로 PyInstaller 빌드
  - `dist/` 내 실행 파일을 ZIP으로 압축하여 artifact 업로드
- **release job:**
  - build 완료 후 실행 (`needs: build`)
  - 모든 artifact 다운로드
  - `softprops/action-gh-release@v2`로 GitHub Release 생성
  - 태그: `{version_tag}-build.{run_number}`
  - 아티팩트: `ScodaDesktop-windows.zip`, `ScodaDesktop-linux.zip`

### 설계 결정

1. **단일 워크플로우:** 빌드가 단순하므로 reusable workflow로 분리하지 않음.
2. **macOS 미포함:** 현재 사용자 없으므로 제외, 필요 시 매트릭스에 추가 가능.
3. **Python 3.12 고정:** 릴리스 빌드는 단일 버전, 다중 버전 테스트는 test.yml에서 커버.
4. **아티팩트 naming:** `ScodaDesktop-{os}.zip` 형태로 통일.

## 수정 파일

| 파일 | 작업 |
|------|------|
| `.github/workflows/release.yml` | 신규 — Manual Release 워크플로우 |
| `devlog/20260223_P13_manual_release_workflow.md` | 신규 — 본 문서 |
| `docs/HANDOFF.md` | P13 완료 반영 |
