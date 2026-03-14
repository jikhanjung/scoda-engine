# P29: Multi-Package Serving — 여러 SCODA 패키지 동시 서빙

**날짜:** 2026-03-13
**목표:** 하나의 scoda-engine 인스턴스에서 여러 SCODA 패키지(trilobase, brachiobase 등)를 동시에 서빙하고, 한 세션 안에서 자유롭게 패키지 간 전환할 수 있도록 한다.

## 배경

현재 scoda-engine은 **단일 패키지 모드**로 동작한다. 서버 시작 시 하나의 패키지를 선택하면 해당 세션 동안 고정된다. trilobase와 brachiobase를 동시에 보려면 두 개의 서버를 각각 다른 포트에 띄워야 한다.

ScodaDesktop에서는 불편하지만 치명적이지 않다. 그러나 Docker 배포 환경에서는 필수적인 기능이다 — 하나의 컨테이너에서 여러 패키지를 서빙해야 리소스 효율적이다.

## 현황 분석

### 이미 갖추어진 기반

| 구성요소 | 상태 | 비고 |
|----------|------|------|
| `PackageRegistry` | ✅ 멀티 패키지 지원 | `scan()`, `get_db(name)`, `list_packages()` 이미 구현 |
| per-request 커넥션 | ✅ | 요청마다 새 SQLite 연결 → 패키지별 격리 자연스러움 |
| 의존성 ATTACH | ✅ | 패키지별 overlay + dependency DB ATTACH 동작 |
| Docker scan | ✅ | `serve_web.py`가 `/data/` 디렉토리의 모든 `.scoda` 스캔 |

### 현재 제약 (변경 필요)

| 제약 | 위치 | 문제 |
|------|------|------|
| Global `_active_package_name` | `scoda_package.py` | 프로세스당 하나의 패키지만 활성 |
| URL 라우팅 없음 | `app.py` 40+ 엔드포인트 | `/api/manifest` 등 모든 경로가 암시적 단일 패키지 |
| 프론트엔드 단일 패키지 가정 | `app.js` | `fetch('/api/manifest')` — 패키지 파라미터 없음 |
| `SCODA_MODE` 글로벌 | `app.py` | viewer/admin 모드가 앱 전체에 고정 |

### SQLite 제한 사항

- **ATTACH 제한**: 기본 10개 (컴파일 시 `SQLITE_MAX_ATTACHED`로 변경 가능)
  - 현재 패키지당: 1 canonical + 1 overlay + N dependency ≈ 2~3개
  - 10개 패키지 동시 서빙 시에도 per-request이므로 ATTACH 제한에 걸리지 않음
- **파일 디스크립터**: per-request 모델이므로 동시 요청 수에 비례
  - Gunicorn 2 workers × 요청 수 → 수백 개 수준, 문제 없음
- **결론: SQLite 측 제한은 multi-package에 장애가 되지 않음**

## 설계

### 접근 방식: URL Prefix 기반 패키지 선택

URL prefix (`/api/{package}/...`)가 REST 의미론상 자연스럽고, 브라우저 히스토리/북마크에 패키지 컨텍스트가 포함된다. FastAPI의 path parameter로 구현하면 자동 문서화(OpenAPI)에도 반영됨.

### 아키텍처

```
┌─────────────────────────────────────────┐
│  Browser                                │
│  ┌─────────────────────────────────┐    │
│  │ Package Selector (dropdown/tab) │    │
│  │  [trilobase ▼] [brachiobase]   │    │
│  └─────────────────────────────────┘    │
│  ↓ fetch('/api/trilobase/manifest')     │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  FastAPI (single instance)              │
│                                         │
│  Path param: /api/{package}/...          │
│  → package_name from URL path           │
│                                         │
│  get_db(package_name)                   │
│  → registry.get_db(package_name)        │
│                                         │
│  Endpoints: mounted under               │
│  /api/{package}/ prefix                 │
└─────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────┐
│  PackageRegistry                        │
│  ├── trilobase  → trilobase-0.3.0.db   │
│  ├── brachiobase → brachiobase-0.2.1.db│
│  └── (future packages...)              │
└─────────────────────────────────────────┘
```

### URL 구조

```
GET /api/packages                              → [{name, version, description}, ...]
GET /api/{package}/manifest                    → 해당 패키지의 manifest
GET /api/{package}/queries/{name}/execute      → 쿼리 실행
GET /api/{package}/...                         → 기타 모든 엔드포인트
```

단일 패키지 모드 호환: `/api/manifest` (prefix 없음) → `_active_package_name` fallback.

### 프론트엔드 변경

1. **Package Selector UI**: 상단 네비게이션에 패키지 선택 드롭다운
2. **URL 기반 상태**: 선택한 패키지가 API URL prefix에 포함 (`/api/trilobase/...`)
3. **API fetch wrapper**: 모든 fetch 호출에 현재 패키지 prefix 자동 추가
4. **패키지 전환 시**: manifest 재로딩, 뷰 초기화

### ScodaDesktop vs Docker

| | ScodaDesktop | Docker |
|---|---|---|
| 패키지 소스 | 로컬 `.scoda` 파일 열기 | `/data/` 디렉토리 스캔 |
| 패키지 전환 | Package Selector UI | 동일 |
| 모드 | viewer/admin 선택 가능 | 환경변수 또는 per-package 설정 |
| 제한 | 메모리 정도 | 파일 디스크립터, 메모리 |

## 구현 단계

### Phase 1: Backend — 패키지 라우팅 레이어

1. `app.py`에 FastAPI sub-application 또는 APIRouter에 `{package}` path param 추가
2. `get_db(package)` 호출로 교체 — path param에서 패키지명 추출
3. `GET /api/packages` 엔드포인트 추가 (패키지 목록)
4. `/api/{package}/...` prefix 라우팅 + `/api/...` fallback (단일 패키지 호환)

### Phase 2: Frontend — Package Selector

1. `/api/packages` 호출하여 사용 가능한 패키지 목록 획득
2. 상단 UI에 패키지 선택 드롭다운/탭 추가
3. API fetch 래퍼에 `/api/{package}/` prefix 자동 첨부
4. 패키지 전환 시 manifest 재로딩 + 뷰 초기화

### Phase 3: serve.py / serve_web.py 통합

1. `serve.py`에 `--multi` 또는 `--packages-dir` 옵션 추가
2. `serve_web.py`에서 `set_active_package()` 대신 registry 전체 활성화
3. Docker 환경변수: `SCODA_PACKAGES` (콤마 구분) 또는 디렉토리 스캔 자동

### Phase 4: ScodaDesktop 지원

1. GUI에서 여러 `.scoda` 파일 동시 열기 지원
2. Package Selector가 열린 패키지 목록 표시
3. 파일 드래그앤드롭으로 패키지 추가

### Phase 5: 테스트 + 문서화

1. 멀티 패키지 시나리오 테스트 (동시 요청, 패키지 전환)
2. Docker Compose 예시 업데이트
3. README / 사용 가이드 반영

## 고려사항

### 하위 호환성
- `/api/{package}/...` prefix 없이 `/api/...`로 호출 시 기존 단일 패키지 모드로 동작
- 기존 CLI (`--db-path`, `--scoda-path`) 그대로 유지
- 프론트엔드도 패키지가 1개일 때는 selector 숨김

### 성능
- per-request 커넥션 모델이므로 패키지 수 증가가 동시 커넥션 수를 늘리지 않음
- 각 요청은 하나의 패키지 DB만 open
- 메모리 사용량: 패키지당 registry 메타데이터 ≈ 수 KB (무시 가능)

### 보안 (Docker)
- `{package}` path param을 registry에 등록된 이름으로만 제한 (path traversal 방지)
- admin 모드: 패키지별로 설정 가능하게 할지, 전역으로 할지 Phase 3에서 결정

### MCP 서버
- 현재 MCP는 단일 패키지 기반
- 멀티 패키지 MCP는 tool 이름에 prefix 추가 (`trilobase.search_genera` vs `brachiobase.search_genera`)
- 별도 Phase로 분리 가능

## 주요 파일

| 파일 | 역할 |
|------|------|
| `scoda_engine/app.py` | 40+ 엔드포인트에 패키지 라우팅 추가 |
| `scoda_engine_core/scoda_package.py` | `PackageRegistry` (이미 준비됨), global state 제거 |
| `scoda_engine/serve.py` | `--multi` 옵션 추가 |
| `scoda_engine/serve_web.py` | 전체 registry 활성화 모드 |
| `scoda_engine/static/js/app.js` | Package Selector UI + fetch 래퍼 |
| `scoda_engine/templates/index.html` | selector 마크업 |
| `deploy/Dockerfile` | `SCODA_PACKAGES` 환경변수 |
| `deploy/docker-compose.yml` | 멀티 패키지 설정 예시 |
