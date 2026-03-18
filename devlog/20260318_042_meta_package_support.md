# 042. Meta-Package 지원 구현

**날짜:** 2026-03-18
**유형:** feat
**관련:** P31 (Meta-Package Engine Support 계획), trilobase P89/134

---

## 개요

paleobase meta-package를 scoda-engine에서 인식·로딩·표시할 수 있도록 4단계에 걸쳐 구현.

## Phase 1: Core 인식

**파일:** `core/scoda_engine_core/scoda_package.py`

ScodaPackage 클래스에 meta-package 지원 추가:

- `kind` property: `manifest.get('kind', 'package')` 반환
- `is_meta_package` property: `kind == 'meta-package'`
- meta-package일 때 `data.db` 추출 생략 (`db_path = None`)
- `verify_checksum()`: meta-package면 항상 True
- `record_count`: meta-package면 0
- `meta_tree` property: ZIP 내 `meta_tree.json` 파싱 반환
- `package_bindings` property: ZIP 내 `package_bindings.json` 파싱 반환

**테스트:** `TestMetaPackage` 클래스 9개 테스트 신규 추가
- meta-package 로드, kind 감지, db_path=None, record_count=0
- checksum skip, meta_tree/bindings 파싱, 일반 패키지와의 구분

## Phase 2: Registry 통합

**파일:** `core/scoda_engine_core/scoda_package.py`

PackageRegistry 업데이트:

- `list_packages()`: `kind` 필드 추가. meta-package일 때 `member_packages` (paleocore 제외한 의존 패키지 목록)
- `get_package()`: `kind` + `meta_tree` + `package_bindings` + `member_packages` 포함
- `get_db()`: meta-package일 때 `:memory:` DB 생성 후 하위 패키지 multi-ATTACH
- `scan()`: 기존 로직 그대로 동작 (db_path=None으로 자연스럽게 등록)

## Phase 3: 합성 트리 API

**파일:** `scoda_engine/app.py`

3개 엔드포인트 신규:

| 엔드포인트 | 용도 |
|-----------|------|
| `GET /api/{pkg}/meta/tree` | meta_tree.json 반환 |
| `GET /api/{pkg}/meta/bindings` | package_bindings.json 반환 |
| `GET /api/{pkg}/meta/composite-tree` | 합성 트리 (full tree / lazy expand) |

`composite-tree` 동작:
- `node_id` 파라미터 없으면: 전체 meta_tree 노드 구조 + 각 노드의 바인딩 정보 + 가용 여부 반환
- `node_id` 지정 시: 해당 노드에 바인딩된 패키지들의 `classification_edge_cache`에서 root_taxon children 조회, 패키지별로 그룹화하여 반환

`/api/{pkg}/manifest` 수정:
- meta-package일 때 전용 manifest 응답 (kind, meta_tree, package_bindings 포함)

## Phase 4: 프론트엔드

### Landing Page (`templates/landing.html`)

- meta-package 카드: `bi-diagram-3` 아이콘 + `META` 배지
- `member_packages` 목록 표시 (예: "5 packages: trilobita, brachiopoda, ...")
- meta-package를 목록 상단에 정렬

### Package Page (`static/js/app.js`)

- `loadManifest()`에서 `kind: "meta-package"` 감지 → `isMetaPackage = true`
- `renderMetaPackageUI()`: composite-tree API 호출 → 트리 렌더링
- `buildMetaTreeNode()`: 재귀적 meta_tree 노드 구성
  - 클릭 시 chevron 토글 + children 표시
  - meta_tree의 하위 노드는 즉시 렌더링
  - 바인딩된 패키지의 taxa는 lazy load (`/meta/composite-tree?node_id=`)
  - taxa 항목에 패키지 배지 + 패키지 페이지 링크
  - child_count 표시
  - 바인딩 없는 Phylum은 회색(비활성) 표시

---

## 검증

- 232 tests passing (기존 223 + meta-package 9)
- trilobase `dist/` 디렉토리에서 paleobase.scoda + 5개 패키지 + paleocore 통합 테스트:
  - `list_packages()`: paleobase가 kind=meta-package, members=[trilobita, brachiopoda, graptolithina, chelicerata, ostracoda]
  - `composite-tree` node:arthropoda 확장: trilobita(Arthropoda→Trilobita), chelicerata(CHELICERATA→3 Classes), ostracoda(OSTRACODA→5 Orders)
  - `composite-tree` node:brachiopoda: BRACHIOPODA→5 children
  - `composite-tree` node:hemichordata: Graptolithina→5 children

## 변경 파일

| 파일 | 변경 |
|------|------|
| `core/scoda_engine_core/scoda_package.py` | ScodaPackage + PackageRegistry meta-package 지원 |
| `scoda_engine/app.py` | meta/tree, meta/bindings, meta/composite-tree API + manifest 분기 |
| `scoda_engine/templates/landing.html` | META 배지, member 표시, 정렬 |
| `scoda_engine/static/js/app.js` | meta-package 감지 + 전용 트리 UI |
| `tests/test_runtime.py` | TestMetaPackage 9개 테스트 |
