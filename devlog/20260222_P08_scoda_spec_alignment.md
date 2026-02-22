# P08: S-5 SCODA 패키지 스펙 정합성 업데이트

**Date:** 2026-02-22
**Type:** Plan + Implementation
**Task:** S-5

---

## Context

`trilobase/docs/scoda_package_architecture.md`에 SCODA 패키지 스펙이 업데이트되었으나, 현재 `scoda-engine` 런타임 코드가 이를 완전히 반영하지 못하고 있음. 주요 gap 5가지를 해결하여 스펙과 코드의 정합성을 확보한다.

## Gap 분석 요약

| Gap | 현재 상태 | 스펙 요구사항 |
|-----|----------|-------------|
| 1. Checksum 검증 | `verify_checksum()` 존재하나 **호출 안 됨** | 패키지 로딩 시 step 6에서 검증 필수 |
| 2. `required` 필드 | 의존성에 `required` 필드 없음 | `"required": true/false`로 필수/선택 구분 |
| 3. 버전 범위 제약 | `"version": "0.1.1"` (단순 문자열, 미사용) | `">=0.1.1,<0.2.0"` (범위 제약, 런타임 검증) |
| 4. 버전 호환성 차단 | 버전 검사 없음 | "Incompatible versions block package loading" |
| 5. CHANGELOG.md | `.scoda` 패키지에 미포함 | optional 파일로 포함 가능 |

**Auto-download**: 미래 작업으로 보류 (SCODA Hub 미구현)

---

## 구현 계획

### Phase 1: 커스텀 예외 클래스 추가

**파일: `core/scoda_engine_core/scoda_package.py`**

ScodaPackage 클래스 앞에 3개 예외 추가:
- `ScodaPackageError(Exception)` — 기본 예외
- `ScodaChecksumError(ScodaPackageError)` — 체크섬 불일치
- `ScodaDependencyError(ScodaPackageError)` — 필수 의존성 오류

**파일: `core/scoda_engine_core/__init__.py`**

새 예외 3개를 re-export에 추가

### Phase 2: SemVer 파싱 및 버전 제약 검사

**파일: `core/scoda_engine_core/scoda_package.py`** (Helpers 섹션)

두 함수 추가:
- `_parse_semver(version_str)` → `(major, minor, patch)` 튜플 반환
  - `"1.2.3"`, `"1.2"`, `"1"` 지원, pre-release 접미사(`-alpha`) 무시
- `_check_version_constraint(actual_version, constraint_str)` → `bool`
  - 지원 연산자: `>=`, `>`, `<=`, `<`, `==`, `!=`
  - 쉼표 구분 AND 조합: `">=0.1.1,<0.2.0"`
  - 빈 문자열/None → `True` (제약 없음)
  - 단순 버전 문자열 `"0.1.1"` → `"==0.1.1"`로 처리 (하위 호환)

순수 stdlib만 사용 (외부 의존성 없음).

### Phase 3: 패키지 로딩 시 Checksum 검증

**파일: `core/scoda_engine_core/scoda_package.py`**

- `ScodaPackage.__init__(scoda_path, verify_checksum=True)` 시그니처 변경
- data.db 추출 후 `self.verify_checksum()` 호출, 실패 시 `ScodaChecksumError` 발생
- 기존 `verify_checksum()` 로직은 checksum 필드 없으면 `True` 반환하므로 **구형 패키지 호환 유지**
- `PackageRegistry.scan()`의 except 절에 `ScodaChecksumError` 추가 (체크섬 실패 패키지는 skip + warning)

### Phase 4: `required` 필드 + 버전 제약 검증

**파일: `core/scoda_engine_core/scoda_package.py`**

**4a. `PackageRegistry`에 `_resolve_and_validate_deps(name)` 메서드 추가:**
- 각 의존성에 대해:
  - `required` 필드 확인 (기본값 `True` — 하위 호환)
  - 의존성 미발견: required면 `ScodaDependencyError`, optional이면 warning
  - 버전 제약 확인: `_check_version_constraint()` 호출
  - 불일치: required면 `ScodaDependencyError`, optional이면 warning + skip

**4b. `PackageRegistry.get_db()` 수정:**
- `_resolve_and_validate_deps()` 호출 후 ATTACH 진행
- optional + 버전불일치 의존성은 ATTACH에서 제외

**4c. Legacy `_resolve_dependencies()` 수정:**
- 동일한 required/version 검증 로직 적용
- `ScodaChecksumError`, `ScodaDependencyError` 처리

### Phase 5: CHANGELOG.md 지원

**파일: `core/scoda_engine_core/scoda_package.py`**

- `ScodaPackage.create()`에 `changelog_path=None` 파라미터 추가
- ZIP 생성 시 `CHANGELOG.md`로 포함
- `ScodaPackage.changelog` 프로퍼티 추가 (읽기 전용, None if absent)

### Phase 6: `__init__.py` export 업데이트

**파일: `core/scoda_engine_core/__init__.py`**

추가 export:
- `ScodaPackageError`, `ScodaChecksumError`, `ScodaDependencyError`
- `_parse_semver`, `_check_version_constraint` (테스트용)

### Phase 7: 테스트 작성

**파일: `tests/test_runtime.py`**

| 테스트 클래스 | 테스트 항목 |
|-------------|-----------|
| `TestSemVer` | 파싱 정상/에러, 제약 검사 (exact, range, empty, !=) |
| `TestChecksumOnLoad` | 정상 로딩, 손상된 패키지 → `ScodaChecksumError`, `verify_checksum=False` |
| `TestDependencyValidation` | required 누락 → 에러, optional 누락 → 계속, 버전 만족/불만족, required 기본값=True |
| `TestChangelog` | create with changelog, changelog 프로퍼티, 없을 때 None |

---

## 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `core/scoda_engine_core/scoda_package.py` | 예외, SemVer, checksum-on-load, dep validation, CHANGELOG |
| `core/scoda_engine_core/__init__.py` | 새 심볼 re-export |
| `tests/test_runtime.py` | 4개 테스트 클래스 추가 |

## 하위 호환성

- `data_checksum_sha256` 없는 패키지 → checksum 스킵 (기존 동작 유지)
- `required` 필드 없는 의존성 → 기본 `True` (기존 암묵적 동작과 동일)
- 단순 버전 문자열 `"0.1.1"` → `==0.1.1`로 처리 (기존 패키지 호환)
- `changelog_path=None` 기본값 → 기존 create() 동작 변경 없음

## 검증 방법

```bash
# 1. 기존 테스트 전부 통과 확인
pytest tests/ -v

# 2. 새 테스트 통과 확인
pytest tests/test_runtime.py -v -k "SemVer or ChecksumOnLoad or DependencyValidation or Changelog"
```
