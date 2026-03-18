# P31 — scoda-engine Meta-Package 지원 계획

**날짜:** 2026-03-18
**유형:** Plan
**관련:** trilobase P89 (Paleobase Meta-Package 설계), trilobase #134 (Stage 0-1 완료)

---

## 1. 배경

trilobase 레포에서 paleobase meta-package의 데이터 파일과 빌드 스크립트가 완성되었다 (Stage 0-1).
`paleobase-0.1.0.scoda`는 `manifest.json` + `meta_tree.json` + `package_bindings.json`을 포함하며, `data.db`는 없다.

이제 scoda-engine에서 이 meta-package를 인식하고, 로딩하고, UI에서 통합 트리를 표시하는 기능이 필요하다.

## 2. 현재 엔진 구조 요약

### 패키지 로딩 흐름

```
PackageRegistry.scan(dir)
  → *.scoda 파일 탐색
  → ScodaPackage(path) 로 manifest 로드
  → _packages dict에 등록
  → get_db(name) 시 SQLite ATTACH (overlay + deps)
```

### 핵심 구성요소

| 파일 | 역할 |
|------|------|
| `core/scoda_engine_core/scoda_package.py` | ScodaPackage 클래스, manifest 로드, 의존성 해석, 체크섬 |
| `core/scoda_engine_core/validate_manifest.py` | manifest 검증 |
| `scoda_engine/app.py` | FastAPI, PackageRegistry, API 엔드포인트 |
| `scoda_engine/static/js/app.js` | 프론트엔드 manifest 로드, 뷰 전환 |
| `scoda_engine/static/js/tree_chart.js` | D3 기반 트리 렌더링 |
| `scoda_engine/templates/landing.html` | 패키지 목록 랜딩 페이지 |

### 의존성 시스템 (이미 구현됨)

- `dependencies` 배열 지원 (name/alias/version/required)
- SemVer 버전 제약 (`>=`, `<`, `,` AND)
- optional/required 구분
- alias 기반 ATTACH

### `kind` 필드

현재 미사용. manifest에 `kind` 필드를 읽거나 처리하는 코드 없음.

## 3. 구현 항목

### 3.1 ScodaPackage — meta-package 인식

**파일:** `core/scoda_engine_core/scoda_package.py`

- [ ] `kind` property 추가: `manifest.get('kind', 'package')` 반환
- [ ] `is_meta_package` property: `kind == 'meta-package'`
- [ ] meta-package일 때 `data.db` 없음 허용 (현재는 없으면 에러)
- [ ] `meta_tree` property: manifest의 `meta_tree_file`로 지정된 JSON 로드
- [ ] `package_bindings` property: manifest의 `package_bindings_file`로 지정된 JSON 로드
- [ ] `verify_checksum()`: meta-package면 skip (data.db 없으므로)
- [ ] `record_count`: meta-package면 0 반환

### 3.2 PackageRegistry — meta-package 등록

**파일:** `scoda_engine/app.py`

- [ ] `scan()`: meta-package도 `_packages`에 등록. `db_path=None`으로 구분.
- [ ] `list_packages()`: meta-package 항목에 `kind: "meta-package"`, `member_packages` 필드 추가
- [ ] `get_db(name)`: meta-package에 대해 호출 시, 하위 패키지들을 multi-ATTACH한 connection 반환 (또는 별도 메서드)
- [ ] 의존성 해석: meta-package의 dependencies를 자동 해석하여 하위 패키지 목록 구성

### 3.3 Meta-Package API 엔드포인트

**파일:** `scoda_engine/app.py`

- [ ] `GET /api/{meta_package}/manifest` — meta-package manifest 반환 (meta_tree + bindings 포함)
- [ ] `GET /api/{meta_package}/meta_tree` — meta_tree.json 반환
- [ ] `GET /api/{meta_package}/bindings` — package_bindings.json 반환
- [ ] `GET /api/{meta_package}/tree` — meta_tree + 바인딩된 패키지의 root taxon children 합성 반환

합성 트리 API 예시:
```json
{
  "nodes": [
    {"id": "meta:life", "label": "Life", "children": ["meta:eukaryota"]},
    {"id": "meta:eukaryota", "label": "Eukaryota", "children": ["meta:metazoa"]},
    {"id": "meta:metazoa", "label": "Metazoa", "children": [
      "meta:arthropoda", "meta:brachiopoda", "meta:hemichordata", "..."
    ]},
    {"id": "meta:arthropoda", "label": "Arthropoda", "children": [
      {"package": "trilobita", "taxon_id": 5345, "name": "Arthropoda", "rank": "Phylum"},
      {"package": "chelicerata", "taxon_id": 506, "name": "Chelicerata", "rank": "Subphylum"},
      {"package": "ostracoda", "taxon_id": 4, "name": "Ostracoda", "rank": "Subclass"}
    ]}
  ]
}
```

### 3.4 Landing Page 업데이트

**파일:** `scoda_engine/templates/landing.html`

- [ ] meta-package 카드: 일반 패키지와 구분 표시 (예: "Meta-Package" 배지)
- [ ] member packages 목록 표시 (dependencies에서 paleocore 제외한 나머지)
- [ ] 클릭 시 meta-package 전용 UI로 이동

### 3.5 Meta-Package 프론트엔드

**파일:** `scoda_engine/static/js/app.js`, `scoda_engine/templates/index.html`

- [ ] manifest의 `kind`가 `"meta-package"`이면 meta-package 모드 활성화
- [ ] meta_tree 기반 트리 렌더링 (기존 tree_chart.js 활용)
- [ ] 노드 확장 시 바인딩된 패키지의 subtree lazy load
- [ ] 패키지 경계 표시 (`[trilobita]` 태그 등)
- [ ] 바인딩 없는 Phylum 노드는 비활성(회색) 표시

### 3.6 테스트

**파일:** `tests/`

- [ ] meta-package .scoda 로딩 테스트 (manifest, meta_tree, bindings 파싱)
- [ ] `kind` 필드 인식 테스트
- [ ] data.db 없는 패키지 허용 테스트
- [ ] 합성 트리 API 응답 테스트
- [ ] 의존성 해석 테스트 (meta-package → 하위 패키지)

## 4. 구현 순서 (권장)

```
Phase 1: Core 인식 (3.1 + 3.6 일부)
  ScodaPackage에서 meta-package 로드 가능하게
  → data.db 없이도 동작
  → kind/meta_tree/bindings property 추가
  → 테스트 작성

Phase 2: Registry 통합 (3.2)
  PackageRegistry에서 meta-package 등록/목록화
  → list_packages()에 kind 표시
  → 랜딩 페이지 업데이트 (3.4)

Phase 3: 합성 트리 API (3.3)
  meta_tree + bindings → 합성 트리 응답 구현
  → 하위 패키지 DB multi-ATTACH
  → root taxon children 조회

Phase 4: 프론트엔드 (3.5)
  meta-package 전용 트리 렌더링
  → lazy loading + 패키지 경계 표시
```

## 5. 기술적 고려사항

### SQLite ATTACH 한도

SQLite 기본 ATTACH 최대 10개. paleobase 시나리오:
- paleocore (1) + trilobita (1) + brachiopoda (1) + graptolithina (1) + chelicerata (1) + ostracoda (1) = 6 ATTACH
- 여유분 4개 (overlay 등)
- 현재는 한도 내. 패키지가 늘어나면 LRU detach 전략 필요.

### data.db 없는 패키지

현재 `ScodaPackage.__init__`에서 `data.db` 존재를 가정하는 부분:
- `verify_checksum()` — data.db SHA-256 검증
- `record_count` — data.db에서 테이블 카운트
- `get_db()` — data.db 추출 후 connection

이 세 곳에 `is_meta_package` 분기를 추가해야 한다.

### 프론트엔드 트리 합성

기존 트리는 단일 DB의 `classification_edge_cache` 쿼리로 구성. meta-package에서는:
1. meta_tree 노드를 최상위로 렌더링
2. 바인딩된 노드 확장 시 해당 패키지의 edge_cache 쿼리
3. 두 종류의 데이터 소스를 하나의 트리에 합성

이 합성 로직은 **백엔드에서 처리**하고, 프론트엔드에는 일반 트리 데이터와 동일한 형식으로 전달하는 것이 깔끔하다.
