# 20260301_025 잘못된 .scoda 파일 오픈 시 에러 처리 보강

**날짜**: 2026-03-01
**기반 커밋**: `1b76163`
**상태**: 완료

## 요약

Hub에서 다운로드한 파일이 유효한 .scoda ZIP이 아닐 때(예: .db 파일을 .scoda 확장자로 저장)
`BadZipFile` 예외가 catch되지 않아 GUI가 멈추는 문제를 수정.

## 문제 상황

1. Hub manifest의 download_url이 `.db` 파일을 가리킬 경우, `download_package()`가
   `.scoda` 접미사를 붙여 저장 (예: `trilobase-assertion-0.1.0.db.scoda`)
2. 파일 내용은 SQLite DB이므로 `zipfile.ZipFile()`에서 `BadZipFile` 예외 발생
3. `ScodaPackage.__init__()`, `PackageRegistry.scan()`, `register_path()`,
   GUI `_on_download_complete()` 어디에서도 `BadZipFile`을 catch하지 않음
4. GUI 콜백에서 미처리 예외로 인해 패키지 목록 갱신이 중단되고 앱이 멈춘 상태로 남음

## 수정 내용

| 파일 | 위치 | 변경 |
|------|------|------|
| `core/scoda_engine_core/scoda_package.py` | `ScodaPackage.__init__()` | `zipfile.BadZipFile` catch → `ValueError`로 변환 |
| `core/scoda_engine_core/scoda_package.py` | `ScodaPackage.__init__()` manifest 읽기 | `json.JSONDecodeError` catch → `ValueError`로 변환 |
| `core/scoda_engine_core/scoda_package.py` | `PackageRegistry.scan()` | except 목록에 `BadZipFile` 추가 (방어) |
| `scoda_engine/gui.py` | `_on_download_complete()` | `except (FileNotFoundError, ValueError)` → `except Exception` (방어) |

## 설계 판단

- **근본 수정**: `ScodaPackage.__init__()`에서 `BadZipFile`을 `ValueError`로 변환.
  기존 모든 호출자가 `ValueError`를 "잘못된 패키지"로 처리하므로 자연스럽게 전파됨.
- **방어적 안전망**: `scan()`과 GUI 콜백에서도 추가 catch하여 향후 예상치 못한 예외에 대비.
- `json.JSONDecodeError`도 동일 패턴으로 처리 (manifest.json이 손상된 경우).
