# S-5: SCODA 패키지 스펙 정합성 업데이트 — 구현 완료

**Date:** 2026-02-22
**Type:** Implementation
**Plan:** `devlog/20260222_P08_scoda_spec_alignment.md`

---

## 변경 요약

SCODA 패키지 스펙과 런타임 코드 사이의 5가지 gap을 해결.

### Gap → 해결

| Gap | 해결 내용 |
|-----|----------|
| 1. Checksum 미호출 | `ScodaPackage.__init__(verify_checksum=True)` — 로딩 시 자동 검증 |
| 2. `required` 필드 없음 | 의존성에 `required` 필드 지원 (기본값 `True`, 하위 호환) |
| 3. 버전 범위 미지원 | `_parse_semver()` + `_check_version_constraint()` — `">=0.1.1,<0.2.0"` 지원 |
| 4. 버전 호환성 차단 없음 | required + 버전 불일치 → `ScodaDependencyError`, optional → skip + warning |
| 5. CHANGELOG.md 미지원 | `create(changelog_path=...)` + `ScodaPackage.changelog` 프로퍼티 |

### 새 예외 클래스

- `ScodaPackageError` — 기본 예외
- `ScodaChecksumError(ScodaPackageError)` — 체크섬 불일치
- `ScodaDependencyError(ScodaPackageError)` — 필수 의존성 오류

## 수정 파일

| 파일 | 변경 |
|------|------|
| `core/scoda_engine_core/scoda_package.py` | 예외 3개, SemVer 2함수, checksum-on-load, dep validation, changelog |
| `core/scoda_engine_core/__init__.py` | 새 심볼 6개 re-export |
| `tests/test_runtime.py` | `TestSemVer`(14), `TestChecksumOnLoad`(5), `TestDependencyValidation`(6), `TestChangelog`(4) — 총 29개 테스트 추가 |
| `docs/HANDOFF.md` | P08/S-5 완료 기록 |

## 하위 호환성

- `data_checksum_sha256` 없는 패키지 → checksum 스킵
- `required` 필드 없는 의존성 → 기본 `True`
- 단순 버전 문자열 `"0.1.1"` → `==0.1.1`로 처리
- `changelog_path=None` 기본값 → 기존 create() 동작 변경 없음

## 테스트 결과

```
225 passed in 61.58s
```
