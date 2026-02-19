# P01: scoda-engine 향후 작업 로드맵

**작성일:** 2026-02-19

---

## 현재 상태

| 항목 | 상태 |
|------|------|
| 프로젝트 분리 | ✅ trilobase에서 독립 repo |
| 패키지명 | `scoda-engine` (import: `scoda_engine`) |
| 테스트 | 191 passed (5 MCP subprocess tests는 CWD에 .scoda 필요) |
| pip install | ✅ `pip install -e ".[dev]"` |

---

## S-1. conftest.py Generic Fixture 전환

**우선순위:** 중간

현재 테스트의 conftest.py가 trilobase 테마(taxonomic_ranks, genus 등) 사용 중.
SCODA 메커니즘 테스트에 도메인 독립적인 generic fixture로 교체.

**작업:**
- 테스트 데이터를 범용 스키마로 교체 (예: items, categories)
- manifest도 범용 테마로 변경
- 기존 122개 runtime + 16개 MCP 테스트 유지

---

## S-2. PyPI 배포

**우선순위:** 중간
**선행:** S-1 권장 (필수는 아님)

`scoda-engine` 패키지를 PyPI에 배포하여 `pip install scoda-engine`으로 설치 가능하게 함.

**작업:**
- pyproject.toml 메타데이터 보강 (license, author, classifiers, URLs)
- README.md PyPI용 정리
- `python -m build` + `twine upload`
- trilobase requirements.txt를 PyPI 참조로 변경

---

## S-3. validate_manifest.py 중복 제거

**우선순위:** 낮음
**선행:** S-2 (PyPI 배포 후)

현재 `validate_manifest.py`가 trilobase와 scoda-engine 양쪽에 존재.
scoda-engine 패키지에서 import하도록 trilobase 측 중복 제거.

---

## S-4. SCODA 백오피스

**우선순위:** 장기 (별도 프로젝트 가능)

.scoda 패키지를 관리/패키징하는 웹 기반 도구.

**범위:**
- manifest 시각적 편집
- 쿼리 검증
- 패키지 빌드 (원클릭 .scoda 생성)
- UID 참조 검증
- dependency 관리

---

## 권장 착수 순서

| 순서 | 항목 | 규모 |
|------|------|------|
| 1 | S-1. conftest Generic Fixture | 소 |
| 2 | S-2. PyPI 배포 | 소 |
| 3 | S-3. validate_manifest 중복 제거 | 소 |
| 4 | S-4. SCODA 백오피스 | 대 |
