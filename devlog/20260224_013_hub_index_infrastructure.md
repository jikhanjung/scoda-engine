# 013: SCODA Hub 인덱스 인프라 구현

**Date:** 2026-02-24
**Plan:** P15
**Status:** Complete (scoda-engine 측)

---

## 변경 요약

SCODA Hub 정적 레지스트리의 scoda-engine 측 인프라를 구현했다.
GitHub REST API로 패키지 repo의 릴리스를 수집하여 `index.json`을 생성하고,
GitHub Pages에 배포하는 워크플로우를 추가했다.

---

## 변경 파일 및 내용

### 1. `hub/sources.json` (신규)

수집 대상 repo 목록. 수동 관리, git 커밋.

```json
[
  {
    "repo": "jikhanjung/trilobase",
    "type": "github_releases"
  }
]
```

새 패키지 repo가 생기면 여기에 항목 추가.

### 2. `scripts/generate_hub_index.py` (신규)

GitHub REST API로 릴리스를 수집하여 `hub/index.json` 생성.

**특징:**
- 순수 Python stdlib (`urllib.request`) — 외부 의존성 없음
- `GITHUB_TOKEN` 환경변수 지원 (rate limit 회피, Actions에서 자동 제공)
- 2단계 수집 전략:
  - Strategy 1: `*.manifest.json` 에셋 다운로드 + 파싱 (메타데이터 풍부)
  - Strategy 2: `.scoda` 파일명 패턴 fallback (`name-version.scoda`)
- 멀티 패키지 릴리스 지원 (하나의 릴리스에 여러 .scoda 포함)
- latest 버전 자동 결정 (semver 정렬)

**CLI 옵션:**
```bash
python scripts/generate_hub_index.py              # index.json 생성
python scripts/generate_hub_index.py --dry-run     # stdout 미리보기
python scripts/generate_hub_index.py --all         # 최신뿐 아니라 전체 릴리스 수집
python scripts/generate_hub_index.py --sources hub/sources.json --output hub/index.json
```

**테스트 결과 (`--dry-run`):**
```
Sources: 1 repo(s)
Fetching releases from jikhanjung/trilobase...
  Found 1 release(s)
  Collected: paleocore v0.1.1
  Collected: trilobase v0.2.2
Generated: 2 package(s), 2 version(s)
```

### 3. `.github/workflows/hub-index.yml` (신규)

Hub 인덱스 생성 + GitHub Pages 배포 워크플로우.

- **트리거**: `workflow_dispatch` (수동) + `schedule` (매주 월요일 00:00 UTC)
- **권한**: `contents: read`, `pages: write`, `id-token: write`
- **동시성**: `group: pages` (중복 배포 방지)
- **Job 1 (generate)**: Python 3.12 설정 → `generate_hub_index.py` 실행 → Pages artifact 업로드
- **Job 2 (deploy)**: `actions/deploy-pages@v4`로 GitHub Pages 배포

### 4. `.gitignore` 업데이트

`hub/index.json`은 자동 생성물이므로 main 브랜치에 커밋하지 않음.

```
# Hub index (auto-generated, deployed to gh-pages)
hub/index.json
```

### 5. `docs/HANDOFF.md` 업데이트

- P15 scoda-engine 측 완료로 마일스톤 추가
- In Progress를 trilobase 측 후속 작업으로 변경
- Next Steps, Document References 업데이트

---

## 아키텍처

```
┌─────────────────────┐     GitHub REST API      ┌────────────────────┐
│  trilobase repo     │ ◄─────────────────────── │  scoda-engine repo  │
│  - Releases         │       (읽기 전용)         │                    │
│    *.scoda          │                           │  hub/sources.json  │
│    *.manifest.json  │                           │  ↓                 │
│    (향후 추가)       │                           │  generate_hub_     │
└─────────────────────┘                           │  index.py          │
                                                  │  ↓                 │
                                                  │  hub/index.json    │
                                                  │  ↓                 │
                                                  │  GitHub Pages      │
                                                  └────────────────────┘
```

---

## 후속 작업 (trilobase repo)

scoda-engine 측은 완료. trilobase repo에서 아래 작업을 하면 Strategy 1이 활성화됨:

1. `create_scoda.py` / `create_paleocore_scoda.py`에 Hub manifest 자동 생성 추가
   - `.scoda` 빌드 직후 `{package_id}.manifest.json` 생성
   - sha256, size_bytes, version, dependencies 등 포함
2. `release.yml`의 files 패턴에 `dist/*.manifest.json` 추가

manifest가 없어도 현재 Strategy 2 (파일명 fallback)로 동작하므로
Hub 인덱스는 즉시 사용 가능하다.
