# P29: Multi-Package Serving 구현

**Date:** 2026-03-14
**Version:** 0.2.5 → 0.3.0

## 개요

하나의 scoda-engine 인스턴스에서 여러 .scoda 패키지를 동시 서빙하도록 리팩토링.
URL prefix 기반 라우팅 (`/api/{package}/...`), 랜딩 페이지, 하위 호환성 유지.

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `core/scoda_engine_core/scoda_package.py` | `register_db()` 메서드 추가, `_set_paths_for_testing()` registry 등록, `check_same_thread=False` |
| `scoda_engine/app.py` | APIRouter 리팩토링, `get_package_db` dependency, 글로벌/페이지 라우트 |
| `scoda_engine/templates/index.html` | `API_BASE` 스크립트 주입, Home breadcrumb 네비게이션 |
| `scoda_engine/templates/landing.html` | 신규: D3 force 다중 패키지 랜딩 페이지 |
| `scoda_engine/static/js/app.js` | `resolveApiUrl()` 유틸, 18개 fetch URL → `${API_BASE}/...` |
| `scoda_engine/serve_web.py` | 디렉토리 모드 `set_active_package()` 제거 |
| `scoda_engine/gui.py` | Start Server 패키지 선택 불요, 전체 패키지 동시 서빙, 버전 표시 |
| `tests/test_runtime.py` | URL `/api/...` → `/api/test/...`, `GET /` redirect 검증 |
| `tests/test_crud.py` | URL `/api/...` → `/api/test/...` |
| `deploy/docker-compose.yml` | 이미지 태그 0.3.0 |
| `pyproject.toml` | version 0.3.0 |
| `scoda_engine/__init__.py` | `__version__` 0.3.0 |

## Phase 1: Backend — APIRouter 리팩토링 (`app.py`)

### `get_package_db` dependency

```python
async def get_package_db(package: str):
    try:
        conn = get_registry().get_db(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    try:
        yield conn
    finally:
        conn.close()
```

- async generator로 구현 — FastAPI가 요청 종료 시 자동 `conn.close()`
- `get_registry().get_db(package)` 호출, KeyError → 404

### Package Router

```python
pkg_router = APIRouter(prefix="/api/{package}")
```

기존 20+ 엔드포인트를 `@pkg_router.get/post/...`로 이동:
- 각 엔드포인트: `conn = get_db()` → `conn: sqlite3.Connection = Depends(get_package_db)`
- 수동 `conn.close()` 제거 (dependency가 처리)
- Helper 함수들 (`_fetch_manifest`, `_execute_query` 등)은 이미 `conn` 파라미터 기반이므로 변경 없음

### 글로벌 엔드포인트

- `GET /api/packages` — `registry.list_packages()` 반환 (신규)
- `GET /healthz` — 패키지 수 포함, DB 연결 불요
- `POST /api/hub/sync` — 기존 유지 (serve_web.py에서 등록)

### 페이지 라우트

- `GET /` — 패키지 1개: `RedirectResponse(/{name}/, 302)`, 여러 개: `landing.html` 렌더
- `GET /{package}/` — `index.html` 렌더 + `package_name` 템플릿 변수 전달
  - 패키지 존재 여부 검증 (`get_registry().get_package()`, 404)

## Phase 2: Frontend — `API_BASE` 도입

### `index.html`

```html
<script>const API_BASE = '/api/{{ package_name }}';</script>
```

Home breadcrumb 네비게이션 추가:
```
🏠 SCODA / Chelicerobase v0.1.0
```
- 집 아이콘 + "SCODA" → `/` 링크 (패키지 목록)
- `/` 구분자 + 패키지명 (manifest 로드 후 동적 표시)

### `app.js`

```javascript
function resolveApiUrl(path) {
    if (path.startsWith('/api/')) {
        return API_BASE + path.slice(4);
    }
    return path;
}
```

- 18개 fetch URL: `/api/manifest` → `${API_BASE}/manifest` 등
- `view.source` URL: `resolveApiUrl()` 로 변환 (예: `/api/genus/123` → `${API_BASE}/genus/123`)
- `/api/hub/sync`는 글로벌이므로 그대로 유지

## Phase 3: 랜딩 페이지 (`landing.html`)

- 신규 템플릿: `scoda_engine/templates/landing.html`
- D3 force simulation: 패키지별 원형 노드가 부유하며 움직이는 배경
- `GET /api/packages`로 데이터 로드
- 패키지 카드 그리드: 이름, 버전, 설명, 레코드 수
- 클릭 시 `/{name}/`으로 이동
- 다크 배경 (#0d1117), 글로우 이펙트, 반응형

## Phase 4: Core 변경 (`scoda_package.py`)

### `PackageRegistry.register_db()`

```python
def register_db(self, name, db_path, overlay_path, extra_dbs=None):
    self._packages[name] = {
        'pkg': None, 'db_path': db_path,
        'overlay_path': overlay_path, 'deps': [],
        '_extra_dbs': extra_dbs or {},
    }
```

- 테스트 / 직접 DB 모드용 — ScodaPackage 래핑 없이 경로만 등록
- `get_db()`에서 `_extra_dbs` 자동 ATTACH 처리

### `_set_paths_for_testing()` 변경

```python
# 기존 동작 유지 + registry에 "test" 이름으로 등록
if _registry is None:
    _registry = PackageRegistry()
_registry.register_db('test', canonical_path, overlay_path, extra_dbs or {})
```

### `check_same_thread=False`

`PackageRegistry.get_db()`의 `sqlite3.connect()`에 추가.
FastAPI async dependency lifecycle에서 connection 생성 스레드와 사용 스레드가 다를 수 있어 필요.

## Phase 5: `serve_web.py`

디렉토리 모드에서 `set_active_package()` 제거:
- 기존: 하나의 패키지 선택 → `set_active_package()`
- 변경: 모든 패키지 동시 서빙, `SCODA_PACKAGE` env var는 `GET /` redirect용으로만 사용

## Phase 6: GUI (`gui.py`)

### Start Server — 패키지 선택 불요

- 기존: 패키지 선택 필수 → Start Server 활성화
- 변경: 패키지가 1개 이상이면 항상 Start Server 활성화
- `set_active_package()` 호출 제거 — 모든 패키지 동시 서빙

### 패키지 목록 — 정보 표시 전용

- Listbox 서버 실행 중 비활성화 제거 — 자유롭게 탐색 가능
- 선택 시 정보만 표시, 서버 동작에 영향 없음

### 헤더 표시

- 단일 패키지: `▶ sample-data v1.0.0`
- 복수 패키지: `▶ Serving N packages`
- 버전 표시: `SCODA Desktop v0.3.0`

### Open Browser

- 패키지 선택 시 `http://localhost:{port}/{name}/`으로 직접 이동
- 미선택 시 `http://localhost:{port}/` (랜딩/redirect)

## Phase 7: 테스트 업데이트

### URL 변환

`_set_paths_for_testing()`이 registry에 `"test"` 패키지를 자동 등록하므로:
- `test_runtime.py`: `/api/manifest` → `/api/test/manifest` (109개소)
- `test_crud.py`: `/api/entities` → `/api/test/entities` (48개소)

### `GET /` 테스트

기존: `GET /` → 200 (HTML)
변경: `GET /` → 302 redirect to `/test/`, follow-up `GET /test/` → 200 (HTML)

### Auto-generated manifest source URL

`/api/auto/detail/{table}?id={id}` — 패키지 prefix 미포함 (frontend `resolveApiUrl()`이 처리)

### 결과

```
303 passed in 71s
```

## 버전 업

- `scoda_engine/__init__.py`: 0.2.5 → 0.3.0
- `pyproject.toml`: 0.2.5 → 0.3.0
- `deploy/docker-compose.yml`: 이미지 태그 0.3.0
