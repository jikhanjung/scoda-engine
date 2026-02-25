# SCODA Hub Manifest Specification

**Version:** 1.0
**Date:** 2026-02-25

---

## 1. Overview

SCODA Hub는 `.scoda` 패키지의 검색, 다운로드, 의존성 해결을 위한 정적 레지스트리이다.
Hub는 세 가지 JSON 스키마로 구성된다:

| 파일 | 위치 | 역할 |
|------|------|------|
| **Hub Manifest** | 패키지 repo Release asset | 개별 패키지의 배포 메타데이터 |
| **Hub Index** | scoda-engine GitHub Pages | 전체 패키지 카탈로그 (자동 생성) |
| **Sources** | `hub/sources.json` | 수집 대상 repo 목록 (수동 관리) |

### .scoda 내부 manifest와의 관계

`.scoda` 내부 `manifest.json`은 **패키지 내용**(데이터 구조, 레코드 수, data.db 무결성)을 기술한다.
Hub Manifest는 **패키지 배포**(다운로드 URL, .scoda 파일 무결성, 크기)를 기술한다.
이 둘은 역할이 다르며, `.scoda`를 열지 않고도 패키지 정보를 알 수 있게 하는 것이 Hub Manifest의 핵심 목적이다.

### SHA-256 이중 구조

| 체크섬 | 대상 | 위치 | 용도 |
|--------|------|------|------|
| `data_checksum_sha256` | `data.db` 파일 | .scoda 내부 manifest | 패키지 데이터 무결성 |
| `sha256` | `.scoda` 파일 전체 | Hub Manifest | 다운로드 무결성 |

---

## 2. Hub Manifest (per-package)

패키지 repo의 GitHub Release에 업로드하는 파일.

**파일명 규칙:** `{package_id}-{version}.manifest.json`

```json
{
  "hub_manifest_version": "1.0",
  "package_id": "trilobase",
  "version": "0.2.2",
  "title": "Trilobase - Genus-level trilobite taxonomy",
  "description": "Genus-level trilobite taxonomy database",
  "license": "CC-BY-4.0",
  "created_at": "2026-02-20T12:00:00Z",
  "provenance": ["Jell & Adrain 2002", "Adrain 2011"],
  "dependencies": {
    "paleocore": ">=0.1.3,<0.2.0"
  },
  "filename": "trilobase-0.2.2.scoda",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 524288,
  "scoda_format_version": "1.0",
  "engine_compat": ">=0.1.0"
}
```

### 필드 정의

| 필드 | 타입 | 필수 | 설명 |
|------|------|:----:|------|
| `hub_manifest_version` | string | O | Hub Manifest 스키마 버전. 현재 `"1.0"` |
| `package_id` | string | O | 패키지 고유 식별자. .scoda 내부 `name`과 동일 |
| `version` | string | O | 패키지 버전. SemVer (`MAJOR.MINOR.PATCH`) |
| `title` | string | O | 사람이 읽을 수 있는 패키지 제목 |
| `description` | string | O | 패키지 설명 |
| `license` | string | - | 라이선스 식별자 (SPDX). 예: `"CC-BY-4.0"` |
| `created_at` | string | - | 패키지 생성 시각. ISO 8601 형식 |
| `provenance` | string[] | - | 데이터 출처 목록 (참고문헌 등) |
| `dependencies` | object | - | 의존 패키지. `{name: version_spec}` 형식 |
| `filename` | string | - | `.scoda` 파일명. 기본값: `{package_id}-{version}.scoda`. Hub Manifest 파일명과 대응 |
| `sha256` | string | O | `.scoda` 파일의 SHA-256 해시 (hex digest) |
| `size_bytes` | integer | - | `.scoda` 파일 크기 (바이트) |
| `scoda_format_version` | string | - | SCODA 포맷 버전. 기본값: `"1.0"` |
| `engine_compat` | string | - | 호환 Engine 버전 범위. 예: `">=0.1.0"` |

### dependencies 형식

키는 패키지 이름, 값은 SemVer 버전 범위 문자열:

```json
{
  "paleocore": ">=0.1.3,<0.2.0"
}
```

의존성이 없으면 빈 객체 `{}` 또는 필드 생략.

### download_url 처리

Hub Manifest에는 `download_url`을 포함하지 **않는다**.
빌드 시점에는 GitHub Release URL이 확정되지 않기 때문이다.
`download_url`은 Hub Index 생성 시 scoda-engine이 GitHub API에서 수집하여 채운다.

---

## 3. Hub Index (`index.json`)

scoda-engine GitHub Pages에 호스팅되는 자동 생성 카탈로그.

**URL:** `https://{user}.github.io/scoda-engine/index.json`

```json
{
  "hub_version": "1.0",
  "generated_at": "2026-02-24T15:00:00+00:00",
  "sources": [
    {"repo": "jikhanjung/trilobase", "type": "github_releases"}
  ],
  "packages": {
    "trilobase": {
      "latest": "0.2.2",
      "versions": {
        "0.2.2": {
          "title": "Trilobase - Genus-level trilobite taxonomy",
          "description": "Genus-level trilobite taxonomy database",
          "download_url": "https://github.com/jikhanjung/trilobase/releases/download/v0.2.2/trilobase-0.2.2.scoda",
          "sha256": "e3b0c44...",
          "size_bytes": 524288,
          "dependencies": {"paleocore": ">=0.1.3,<0.2.0"},
          "engine_compat": ">=0.1.0",
          "scoda_format_version": "1.0",
          "license": "CC-BY-4.0",
          "created_at": "2026-02-20T12:00:00Z",
          "source_release": "https://github.com/jikhanjung/trilobase/releases/tag/v0.2.2"
        }
      }
    }
  }
}
```

### 루트 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `hub_version` | string | Hub Index 스키마 버전. 현재 `"1.0"` |
| `generated_at` | string | 인덱스 생성 시각. ISO 8601 형식 |
| `sources` | object[] | 수집 대상 repo 목록 |
| `packages` | object | 패키지 카탈로그. 키: package_id |

### packages.{package_id}

| 필드 | 타입 | 설명 |
|------|------|------|
| `latest` | string | 최신 버전 문자열 (SemVer 기준 정렬) |
| `versions` | object | 버전별 엔트리. 키: 버전 문자열 |

### packages.{package_id}.versions.{version} (Version Entry)

| 필드 | 타입 | 설명 |
|------|------|------|
| `title` | string | 패키지 제목 |
| `description` | string | 패키지 설명 |
| `download_url` | string | `.scoda` 파일 다운로드 URL |
| `sha256` | string | `.scoda` 파일 SHA-256 해시 |
| `size_bytes` | integer | `.scoda` 파일 크기 (바이트) |
| `dependencies` | object | 의존 패키지 `{name: version_spec}` |
| `engine_compat` | string | 호환 Engine 버전 범위 |
| `scoda_format_version` | string | SCODA 포맷 버전 |
| `license` | string | 라이선스 식별자 |
| `created_at` | string | 패키지 생성 시각 |
| `source_release` | string | GitHub Release 페이지 URL |

### 수집 전략과 Hub Manifest의 역할

Index 생성 스크립트(`generate_hub_index.py`)는 두 가지 전략으로 동작한다.
Hub Manifest는 **선택 사항**이며, 없어도 기본적인 패키지 검색과 다운로드는 가능하다.

#### Strategy 1: Hub Manifest 파싱 (manifest 있는 경우)

릴리스에 `*.manifest.json` asset이 있으면, 이를 다운로드하여 파싱한다.
모든 메타데이터 필드가 채워지며, SHA-256 검증과 의존성 해결이 완전히 동작한다.

#### Strategy 2: Fallback (manifest 없는 경우)

릴리스에 `*.manifest.json`이 없으면, `.scoda` 파일명에서 메타데이터를 추론한다.
파일명 패턴 `{package_id}-{version}.scoda` (예: `trilobase-0.2.2.scoda`)에서
package_id와 version을 추출하고, `download_url`과 `size_bytes`는 GitHub API에서 수집한다.

#### 전략별 데이터 비교

| 필드 | Strategy 1 (manifest) | Strategy 2 (fallback) |
|------|:---------------------:|:---------------------:|
| `download_url` | O | O |
| `size_bytes` | O | O |
| `title` | 실제 제목 | package_id 그대로 |
| `description` | O | 빈 문자열 |
| `sha256` | O | 빈 문자열 |
| `dependencies` | O | `{}` |
| `license` | O | 빈 문자열 |
| `engine_compat` | O | 빈 문자열 |
| `created_at` | manifest 값 | release published_at |

#### Fallback의 제약

Fallback 모드에서는 다음 기능이 **동작하지 않는다**:

- **SHA-256 검증**: `sha256`이 빈 문자열이므로 다운로드 무결성 검증 불가
- **의존성 자동 해결**: `dependencies`가 빈 객체이므로 `resolve_download_order()`가
  의존 패키지를 인식하지 못함. 예를 들어 trilobase→paleocore 의존성이 있어도
  trilobase만 다운로드되고 paleocore는 자동으로 함께 받아지지 않음
- **메타데이터 표시**: 제목, 설명, 라이선스 등이 표시되지 않아 사용자 경험이 저하됨

따라서 Fallback은 **빠른 시작용**이며, 프로덕션 릴리스에서는 Hub Manifest를 함께 업로드하는 것을 권장한다.

---

## 4. Sources (`hub/sources.json`)

수집 대상 repo 목록. 수동으로 관리하며 git에 커밋된다.

```json
[
  {
    "repo": "jikhanjung/trilobase",
    "type": "github_releases"
  }
]
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `repo` | string | GitHub repo (`owner/repo` 형식) |
| `type` | string | 소스 유형. 현재 `"github_releases"`만 지원 |

---

## 5. 수집 워크플로우

```
패키지 repo (trilobase)                  scoda-engine repo
┌──────────────────────────┐             ┌───────────────────────────┐
│  GitHub Release          │  read-only  │  hub/sources.json         │
│  ├── *.scoda             │◄────────────│  scripts/generate_hub_   │
│  └── *.manifest.json     │  GitHub API │    index.py               │
└──────────────────────────┘             │  → hub/index.json         │
                                         │  → GitHub Pages 배포      │
                                         └───────────────────────────┘
```

### 처리 순서

1. `hub/sources.json`에서 수집 대상 repo 목록 읽기
2. 각 repo의 릴리스를 GitHub REST API로 조회
3. `*.manifest.json` asset이 있으면 파싱 (Strategy 1)
4. 없으면 `.scoda` 파일명에서 추론 (Strategy 2 — Fallback)
5. `download_url`은 GitHub API의 `browser_download_url`에서 수집
6. 버전별로 병합하여 `index.json` 생성
7. `gh-pages` 브랜치에 배포

### 트리거

- `workflow_dispatch` (수동 실행)
- `schedule` (일간 cron)

### 스크립트

```bash
# 생성
python scripts/generate_hub_index.py

# dry-run (stdout 출력, 파일 미생성)
python scripts/generate_hub_index.py --dry-run

# 전체 버전 포함 (기본은 최신만)
python scripts/generate_hub_index.py --all
```

---

## 6. 클라이언트 동작

Hub 클라이언트 (`scoda_engine_core.hub_client`)가 수행하는 동작:

### 인덱스 조회

```python
from scoda_engine_core.hub_client import fetch_hub_index

index = fetch_hub_index()  # SCODA_HUB_URL 환경변수 또는 기본 URL 사용
```

### 로컬 비교

```python
from scoda_engine_core.hub_client import compare_with_local

result = compare_with_local(index, local_packages)
# result["available"]   — 미설치 패키지
# result["updatable"]   — 업데이트 가능 패키지
# result["up_to_date"]  — 최신 상태 패키지
```

### 의존성 해결 및 다운로드

```python
from scoda_engine_core.hub_client import resolve_download_order, download_package

order = resolve_download_order(index, "trilobase", local_packages)
# → [{"name": "paleocore", ...}, {"name": "trilobase", ...}]  (의존성 우선)

for pkg in order:
    path = download_package(
        pkg["entry"]["download_url"],
        dest_dir="/path/to/packages",
        expected_sha256=pkg["entry"].get("sha256"),
    )
```

### SHA-256 검증

다운로드 시 `expected_sha256`이 제공되면 자동 검증한다.
불일치 시 `HubChecksumError` 발생, 임시 파일 자동 삭제.

---

## 7. Hub Manifest 생성 가이드 (패키지 빌더용)

패키지 빌드 스크립트에서 `.scoda` 생성 직후에 Hub Manifest를 함께 생성한다.

```python
import hashlib, json, os

def generate_hub_manifest(scoda_path, package_id, version, title,
                          description="", license="", dependencies=None,
                          provenance=None, scoda_format_version="1.0",
                          engine_compat=""):
    """Generate a Hub manifest JSON file alongside the .scoda file."""
    # SHA-256 of .scoda file
    sha256 = hashlib.sha256()
    with open(scoda_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    manifest = {
        "hub_manifest_version": "1.0",
        "package_id": package_id,
        "version": version,
        "title": title,
        "description": description,
        "license": license,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance or [],
        "dependencies": dependencies or {},
        "filename": os.path.basename(scoda_path),
        "sha256": sha256.hexdigest(),
        "size_bytes": os.path.getsize(scoda_path),
        "scoda_format_version": scoda_format_version,
        "engine_compat": engine_compat,
    }

    out_dir = os.path.dirname(scoda_path)
    manifest_path = os.path.join(out_dir, f"{package_id}-{version}.manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return manifest_path
```

### GitHub Release 업로드

```yaml
# release.yml
- name: Upload release assets
  run: |
    gh release upload ${{ github.ref_name }} \
      dist/*.scoda \
      dist/*.manifest.json
```

---

## 8. 향후 확장 (예약 필드)

현재 사용하지 않지만 향후 버전에서 추가될 수 있는 필드:

| 필드 | 설명 |
|------|------|
| `deprecated` | boolean — 패키지 폐기 여부 |
| `replaced_by` | string — 대체 패키지 ID |
| `signature` | string — 패키지 서명 (코드 서명) |
| `tags` | string[] — 검색용 태그 |
| `homepage` | string — 프로젝트 홈페이지 URL |

---

## 9. 참고

- 설계 문서: `devlog/20260224_P15_scoda_hub_static_registry.md`
- Index 생성 스크립트: `scripts/generate_hub_index.py`
- Hub 클라이언트: `core/scoda_engine_core/hub_client.py`
- .scoda 내부 manifest 스펙: `docs/SCODA_WHITEPAPER.md` Section 2.2
