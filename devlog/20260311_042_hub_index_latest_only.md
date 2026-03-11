# Hub Index: latest 릴리스만 포함하도록 변경

**날짜**: 2026-03-11

## 배경

GitHub Pages 워크플로우(`pages.yml`)에서 `generate_hub_index.py --all`로 Hub 인덱스를 생성하고 있어 모든 릴리스 버전이 누적되었다. 클라이언트가 필요로 하는 것은 최신 버전뿐이므로 불필요한 데이터.

## 변경

- `.github/workflows/pages.yml`: `--all` 플래그 제거
- `generate_hub_index.py`는 기본 동작이 latest release만 fetch → 변경 없음

## 참고

`--all` 옵션은 CLI에서 수동 실행 시 전체 버전 확인용으로 유지.
