# P15: SCODA Hub 정적 레지스트리 설계 검토

**Date:** 2026-02-24
**Status:** Review

---

## 1. 논의 요약

사용자가 .scoda 패키지를 발견하고 다운로드할 수 있는 "SCODA Hub"가 필요하다.
현 단계에서는 **정적 레지스트리(Static Registry)** 로 시작하고,
나중에 필요해지면 서비스형 Hub로 확장하는 2단계 전략이 합의되었다.

### 합의된 1단계 구조

- `.scoda` 파일: GitHub Releases에 업로드
- 패키지 목록: scoda-engine GitHub Pages에 `index.json` 호스팅
- scoda-engine이 index.json을 읽어 목록 표시 + 다운로드 + SHA-256 검증

### 수집 전략

**방식 (1): scoda-engine이 패키지 repo들의 릴리스를 수집해서 index.json 생성**

- trilobase repo는 Release에 `.scoda` + `*.manifest.json` 업로드만 함
- scoda-engine repo의 GitHub Actions가 수집 → index.json 재생성 → Pages 배포
- 크로스 레포 쓰기 권한 불필요 (읽기만)

---

## 2. 현재 구조 분석

### trilobase repo의 .scoda 빌드 파이프라인

trilobase repo (`/mnt/d/projects/trilobase/`)에서 실제 `.scoda` 패키지를 빌드하고 있다.

**빌드 스크립트** (각 패키지별 독립 스크립트):

| 스크립트 | 패키지 | 현재 버전 |
|----------|--------|-----------|
| `scripts/create_scoda.py` | trilobase | 0.2.2 |
| `scripts/create_paleocore_scoda.py` | paleocore | 0.1.1 |

**`create_scoda.py` 처리 순서**:
1. `artifact_metadata`에서 버전 읽기
2. `validate_db()` — 매니페스트 검증
3. `ScodaPackage.create()` 호출 (metadata에 dependencies 주입)
4. `mcp_tools.json`, `CHANGELOG.md`, SPA assets(옵션) 포함
5. 결과 검증 (checksum, 메타 출력)

**릴리스 워크플로우** (`trilobase/.github/workflows/release.yml`):
- 트리거: `v*.*.*` 태그 push
- scoda-engine을 clone해서 의존성 설치
- `pytest tests/` 게이트 통과 후
- `create_paleocore_scoda.py` → `create_scoda.py` 순서로 빌드
- GitHub Release 생성, `.scoda` 파일 2개 업로드

**현재 빌드 산출물** (`trilobase/dist/`):

```
trilobase-0.2.2.scoda    (1.5 MB)
paleocore-0.1.1.scoda    (301 KB)
```

**Hub manifest 연동 포인트**:
- `create_scoda.py`가 이미 모든 메타데이터를 알고 있음
  (version, dependencies, description, checksum 등)
- `.scoda` 생성 직후에 Hub manifest를 함께 생성하는 게 가장 자연스러움
- `release.yml`에 manifest 업로드 step 1줄만 추가하면 됨

### .scoda 내부 manifest (이미 존재)

`ScodaPackage.create()`가 생성하는 `manifest.json`:

```json
{
  "format": "scoda",
  "format_version": "1.0",
  "name": "trilobase",
  "version": "0.2.2",
  "title": "Trilobase - Genus-level trilobite taxonomy",
  "description": "...",
  "created_at": "2026-02-20T...",
  "license": "CC-BY-4.0",
  "authors": [],
  "data_file": "data.db",
  "record_count": 1234,
  "data_checksum_sha256": "abc123...",
  "dependencies": [{"name": "paleocore", "alias": "pc", "version": ">=0.1,<0.3"}]
}
```

### Hub manifest에 추가로 필요한 필드

.scoda 내부 manifest는 **패키지 내용**을 설명한다.
Hub manifest는 **패키지 배포**를 설명한다. 이 둘은 역할이 다르다.

| 필드 | .scoda 내부 | Hub manifest | 비고 |
|------|:-----------:|:------------:|------|
| name/version/description | O | O | 중복이지만 Hub는 .scoda를 열지 않고 알아야 함 |
| download_url | - | **O** | Hub 핵심 |
| sha256 (.scoda 파일 자체) | - | **O** | .scoda 파일의 무결성 검증 |
| size_bytes | - | **O** | 다운로드 전 용량 표시 |
| created_at | O | O | |
| dependencies | O | O | 의존성 동시 다운로드에 필요 |
| provenance | - | 권장 | 요약 수준 (출처 표시) |
| engine_compat | - | 권장 | 호환 Engine 버전 범위 |
| scoda_schema_version | - | 권장 | format_version 대응 |
| deprecated / replaced_by | - | 나중 | 수명주기 관리 |

---

## 3. 설계 제안

### 3.1 Hub Manifest 스키마 (per-package)

패키지 repo의 릴리스에 함께 업로드하는 파일: `{package_id}-{version}.manifest.json`

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
  "download_url": "https://github.com/user/trilobase/releases/download/v0.2.2/trilobase-0.2.2.scoda",
  "filename": "trilobase-0.2.2.scoda",
  "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "size_bytes": 524288,
  "scoda_format_version": "1.0",
  "engine_compat": ">=0.1.0"
}
```

### 3.2 index.json 스키마 (Hub 카탈로그)

scoda-engine GitHub Pages에 호스팅: `https://<user>.github.io/scoda-engine/index.json`

```json
{
  "hub_version": "1.0",
  "generated_at": "2026-02-24T15:00:00Z",
  "sources": [
    {"repo": "user/trilobase", "type": "github_releases"}
  ],
  "packages": {
    "trilobase": {
      "latest": "0.2.2",
      "versions": {
        "0.2.2": {
          "title": "Trilobase - Genus-level trilobite taxonomy",
          "description": "Genus-level trilobite taxonomy database",
          "download_url": "https://github.com/.../trilobase-0.2.2.scoda",
          "sha256": "e3b0c44...",
          "size_bytes": 524288,
          "dependencies": {"paleocore": ">=0.1.3,<0.2.0"},
          "engine_compat": ">=0.1.0",
          "created_at": "2026-02-20T12:00:00Z"
        }
      }
    },
    "paleocore": {
      "latest": "0.1.3",
      "versions": {
        "0.1.3": {
          "title": "PaleoCore Reference Data",
          "description": "Shared reference data for paleontology packages",
          "download_url": "https://github.com/.../paleocore-0.1.3.scoda",
          "sha256": "abc123...",
          "size_bytes": 262144,
          "dependencies": {},
          "engine_compat": ">=0.1.0",
          "created_at": "2026-02-20T12:00:00Z"
        }
      }
    }
  }
}
```

### 3.3 멀티 패키지 릴리스 (trilobase repo)

trilobase repo에서 릴리스 시 업로드하는 아티팩트:

```
trilobase-0.2.2.scoda
trilobase-0.2.2.manifest.json
paleocore-0.1.3.scoda
paleocore-0.1.3.manifest.json
```

- 두 패키지의 버전은 독립적 (항상 같이 올릴 필요 없음)
- 릴리스 태그: `v0.2.2` (trilobase 주 버전 기준)
- paleocore만 업데이트할 때도 새 릴리스 태그 필요 → 나중에 repo 분리 고려

### 3.4 수집 워크플로우 (scoda-engine repo)

```
┌─────────────────────┐     GitHub API (read)     ┌────────────────────┐
│  trilobase repo     │ ◄─────────────────────── │  scoda-engine repo  │
│  - Releases         │                           │  - hub/sources.json │
│    *.manifest.json  │                           │  - Actions (cron    │
│    *.scoda          │                           │    or dispatch)     │
└─────────────────────┘                           │  - generate index   │
                                                  │  → hub/index.json   │
                                                  │  - deploy to Pages  │
                                                  └────────────────────┘
```

#### 수집 대상 설정: `hub/sources.json`

수집 대상 repo 목록은 `hub/sources.json`에 기록한다.
이 파일은 수동으로 관리하며 git에 커밋된다.

```
hub/
├── sources.json       # 수집 대상 repo 목록 (수동 관리, git 커밋)
└── index.json         # 생성 결과 (자동 생성, gh-pages 브랜치 or .gitignore)
```

`hub/sources.json` 예시:

```json
[
  {
    "repo": "jikhanjung/trilobase",
    "type": "github_releases"
  }
]
```

새 패키지 repo가 생기면 여기에 항목을 추가하기만 하면 된다.
`index.json`은 자동 생성물이므로 main 브랜치에는 커밋하지 않고,
gh-pages 브랜치에만 배포하거나 `.gitignore`에 추가한다.

**워크플로우 트리거**: `workflow_dispatch` (수동) + `schedule` (주 1회 cron)

**처리 순서**:
1. `hub/sources.json`에서 수집 대상 repo 목록 읽기
2. 각 repo의 최신 릴리스에서 `*.manifest.json` 다운로드
3. manifest들을 병합하여 `index.json` 생성
4. `gh-pages` 브랜치에 배포

#### 릴리스 수집 방법: GitHub API

scoda-engine Actions에서 trilobase 등 외부 repo의 최신 릴리스 정보를
읽는 방법. public repo이므로 인증 없이도 가능하지만,
Actions에서는 rate limit 회피를 위해 자동 제공되는 `GITHUB_TOKEN`을 사용하는 게 좋다.

**GitHub CLI (`gh`)** — Actions에서 가장 간편:

```bash
# 최신 릴리스의 태그명 + asset 목록
gh release view --repo jikhanjung/trilobase --json tagName,assets

# asset별 파일명 + 다운로드 URL 추출
gh release view --repo jikhanjung/trilobase \
  --json assets --jq '.assets[] | {name, url}'

# *.manifest.json만 필터링해서 다운로드
gh release download --repo jikhanjung/trilobase \
  --pattern '*.manifest.json' --dir /tmp/manifests
```

**REST API** (대안):

```bash
# 최신 릴리스 (tag_name, assets[].name, assets[].browser_download_url)
curl -s https://api.github.com/repos/jikhanjung/trilobase/releases/latest
```

#### index 생성 스크립트 의사코드

```python
# scripts/generate_hub_index.py (scoda-engine repo)
import json, subprocess

with open('hub/sources.json') as f:
    sources = json.load(f)  # [{"repo": "jikhanjung/trilobase"}, ...]

packages = {}
for src in sources:
    repo = src['repo']
    # 1) 최신 릴리스의 asset 목록 가져오기
    result = subprocess.run(
        ['gh', 'release', 'view', '--repo', repo,
         '--json', 'tagName,assets'],
        capture_output=True, text=True)
    release = json.loads(result.stdout)

    # 2) *.manifest.json 다운로드 + 파싱
    for asset in release['assets']:
        if asset['name'].endswith('.manifest.json'):
            manifest = download_and_parse(asset['url'])
            pkg_id = manifest['package_id']
            version = manifest['version']

            # 3) 같은 릴리스에서 .scoda asset의 URL/size 수집
            scoda_asset = find_asset(release, f"{pkg_id}-{version}.scoda")

            packages.setdefault(pkg_id, {"latest": version, "versions": {}})
            packages[pkg_id]["latest"] = version
            packages[pkg_id]["versions"][version] = {
                **manifest,
                "download_url": scoda_asset['url'],
                "size_bytes": scoda_asset['size'],
            }

# 4) index.json 생성
index = {
    "hub_version": "1.0",
    "generated_at": now_iso(),
    "sources": sources,
    "packages": packages,
}
with open('hub/index.json', 'w') as f:
    json.dump(index, f, indent=2)
```

이 스크립트를 Actions workflow에서 실행하면:
- 외부 repo에 대한 **읽기 권한만** 필요 (쓰기 불필요)
- `GITHUB_TOKEN`은 Actions에 자동 제공 (별도 secret 설정 불필요)
- `download_url`은 이 시점에 GitHub API에서 정확한 값을 가져오므로,
  trilobase 빌드 시점에 URL을 예측할 필요가 없음

---

## 4. 핵심 설계 원칙 확인

논의에서 나온 원칙들이 현재 코드베이스와 잘 맞는지 확인:

### Hub는 "디렉토리"이지 "저장소"가 아니다

- **맞음**: Hub(index.json)는 위치 + 무결성 + 의존성만 제공
- 패키지 내용 해석은 항상 SCODA Engine이 담당
- `.scoda` 내부 manifest와 Hub manifest의 **역할 분리**가 명확함

### 기존 구조와의 정합성

| 기존 구조 | Hub 연동 포인트 |
|-----------|-----------------|
| `PackageRegistry.register_path()` (P14) | Hub에서 다운로드한 `.scoda`를 이 API로 로드 |
| `ScodaPackage.create()` | `.scoda` 내부 manifest 생성 (Hub manifest와 별개) |
| `scripts/release.py` | Hub manifest 생성 기능을 여기에 추가하면 자연스러움 |
| `.github/workflows/release.yml` | 현재는 Engine EXE만 배포. Hub index 생성 워크플로우는 별도 |
| `SCODA_PACKAGE_PATH` 환경변수 | Hub 다운로드 후 이 변수로 로드 가능 |

### SHA-256 이중 구조

- `.scoda` **내부**: `data_checksum_sha256` → `data.db` 파일의 해시 (패키지 무결성)
- Hub **manifest**: `sha256` → `.scoda` 파일 자체의 해시 (다운로드 무결성)
- 두 가지는 역할이 다르므로 **둘 다 필요**

---

## 5. 구현 범위 (단계별)

### Phase 0: 스키마 확정 + 수동 운영

- Hub manifest JSON 스키마 확정
- trilobase repo에서 수동으로 `*.manifest.json` 작성 + 릴리스 업로드
- scoda-engine에 `hub-sources.json` + index 생성 스크립트 추가
- GitHub Pages 배포 설정

### Phase 1: 자동화

- trilobase release workflow에서 `*.manifest.json` 자동 생성
- scoda-engine에 index 수집/생성 워크플로우 추가 (cron + dispatch)

### Phase 2: Engine 통합

- GUI/CLI에서 Hub index 조회 기능
- 패키지 다운로드 + SHA-256 검증 + `register_path()` 자동 로드
- 의존성 자동 해결 (dependency 동시 다운로드)

### 나중 (서비스형 Hub)

- 비공개 패키지, 인증, 검색, 통계, 서명

---

## 6. 미결 사항

### 6.1 Hub manifest를 누가 생성하나?

- (a) `trilobase/scripts/create_scoda.py` 확장 — `.scoda` 빌드 직후에 함께 생성
- (b) scoda-engine `scripts/release.py` 확장
- (c) trilobase release workflow에서 별도 스크립트

**추천: (a)** — `create_scoda.py`가 이미 version, dependencies, checksum 등 모든 정보를 알고 있음.
`.scoda` 생성 직후에 sha256(`.scoda` 파일)과 size_bytes를 계산해서 manifest를 쓰면 된다.
`create_paleocore_scoda.py`에도 동일 패턴 적용.

구현 예시 (create_scoda.py 끝부분에 추가):
```python
# Hub manifest 생성
hub_manifest = {
    "hub_manifest_version": "1.0",
    "package_id": pkg.name,
    "version": pkg.version,
    ...
    "sha256": _sha256_file(result),
    "size_bytes": os.path.getsize(result),
}
manifest_path = os.path.join(DEFAULT_OUTPUT_DIR, f"{pkg.name}-{pkg.version}.manifest.json")
with open(manifest_path, 'w') as f:
    json.dump(hub_manifest, f, indent=2)
```

release.yml 변경은 files 패턴에 `dist/*.manifest.json` 추가뿐:
```yaml
files: |
  dist/trilobase-*.scoda
  dist/paleocore-*.scoda
  dist/*.manifest.json
```

### 6.2 index.json 구조: flat vs nested?

- 현재 제안: nested (`packages.{name}.versions.{ver}`)
- 패키지 수가 적은 동안은 단일 파일로 충분
- 50개 이상이면 per-package 분리 고려 (`{package_id}/manifest.json`)

### 6.3 Engine 버전 호환성 (`engine_compat`) 검증 시점

- 다운로드 전 경고? 로드 시 경고? 차단?
- 추천: 경고만 (차단은 나중에)

### 6.4 paleocore repo 분리 시점

- 다른 패키지(brachiobase 등)가 paleocore에 의존하기 시작하면 분리
- 지금은 trilobase repo 안에서 멀티 패키지 릴리스로 충분

### 6.5 download_url의 결정 시점

- `create_scoda.py`가 빌드 시점에는 GitHub Release URL을 모름
  (릴리스 태그가 아직 없음)
- **선택지**:
  - (a) 빌드 스크립트는 `download_url`을 빈 값으로 두고,
    release workflow에서 태그/URL을 주입 → manifest 재작성
  - (b) URL 패턴이 고정이므로 빌드 시 예측 가능:
    `https://github.com/{owner}/{repo}/releases/download/v{version}/{filename}`
  - (c) scoda-engine의 index 생성 스크립트가 GitHub API로 실제 URL을 수집
- **추천: (c)** — Hub가 수집할 때 GitHub API에서 정확한 asset URL을 가져오므로,
  Hub manifest에 `download_url`을 빈 값으로 두거나 아예 넣지 않아도 됨.
  index.json 생성 시 scoda-engine이 채움.

이 경우 Hub manifest의 역할은 "패키지 메타데이터 선언"에 집중하고,
`download_url`은 index.json에서만 존재하게 됨. 이렇게 하면
**manifest를 빌드 시점에 완전히 확정**할 수 있어서 가장 깔끔함.
