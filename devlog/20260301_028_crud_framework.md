# 028: Manifest-Driven CRUD Framework

**Date**: 2026-03-01

## Summary

scoda-engine에 manifest 기반 제네릭 CRUD 프레임워크를 추가했다. manifest의 `editable_entities` 섹션에서 엔티티 스키마를 정의하면, 자동으로 REST API 엔드포인트와 편집 UI가 생성된다.

## Changes

### New Files
- **`scoda_engine/entity_schema.py`**: `FieldDef`, `EntitySchema` 데이터클래스 + `parse_editable_entities()`, `validate_input()` 유틸리티
- **`scoda_engine/crud_engine.py`**: `CrudEngine` — parameterized SQL 기반 CRUD 엔진. FK 검증, unique 제약, post-mutation 훅, FK autocomplete 검색 지원
- **`tests/test_crud.py`**: 27개 CRUD 테스트 (CRUD 연산, pagination, search, validation, auth guards)

### Modified Files
- **`scoda_engine/serve.py`**: `--db-path`, `--mode admin|viewer` CLI 인자 추가. 경로 resolve를 `os.chdir()` 전에 처리
- **`scoda_engine/app.py`**: `SCODA_MODE` 전역, `_require_admin()` 가드, `ManifestResponse`에 `mode` 필드 추가. REST 엔드포인트 10개 (`/api/entities/*`, `/api/search/*`)
- **`scoda_engine/static/js/app.js`**: Admin 모드 UI — detail 모달 Edit/Delete 버튼, 목록 Add 버튼, linked_table 인라인 CRUD, FK autocomplete 검색, `readonly_on_edit` 지원, PLACED_IN rank 필터링
- **`scoda_engine/templates/index.html`**: 모달 헤더 레이아웃 조정
- **`core/scoda_engine_core/validate_manifest.py`**: `editable_entities` 검증 규칙
- **`tests/conftest.py`**: `crud_db`, `crud_client`, `crud_viewer_client` fixture

## Key Design Decisions

1. **Admin/Viewer 모드 분리**: `--mode admin`은 `--db-path`와만 사용 가능. `.scoda` 패키지는 항상 읽기 전용
2. **Manifest-driven**: 스키마, 연산, 제약, 훅 모두 manifest에 선언 — 엔진 코드 변경 없이 도메인 적용
3. **FK autocomplete**: 검색 결과에 non-FK 필드 처음 3개 표시 (text + integer 포함). `fkDisplayLabel()`로 "Name (Type)" 형식 통일
4. **`readonly_on_edit`**: 필드 속성으로 편집 시 읽기 전용 처리
5. **Rank 필터링**: PLACED_IN predicate일 때 object_taxon 검색에 상위 rank만 필터

## API Endpoints

| Method | Path | Mode | Description |
|--------|------|------|-------------|
| GET | `/api/entities` | all | 엔티티 타입 + 스키마 |
| GET | `/api/entities/{type}` | all | 목록 (pagination, search) |
| GET | `/api/entities/{type}/{pk}` | all | 단건 조회 |
| POST | `/api/entities/{type}` | admin | 생성 → 201 |
| PATCH | `/api/entities/{type}/{pk}` | admin | 부분 수정 |
| DELETE | `/api/entities/{type}/{pk}` | admin | 삭제 |
| POST | `/api/entities/{type}/hooks/{name}` | admin | 수동 훅 실행 |
| GET | `/api/search/{type}?q=...` | all | FK autocomplete |

## Test Results

- scoda-engine: 303 passed (276 기존 + 27 신규 CRUD)
