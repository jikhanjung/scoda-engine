"""
Tests for SCODA Desktop runtime (generic viewer, package management, API metadata).
"""

import json
import sqlite3
import os
import stat
import sys
import tempfile
import zipfile

import pytest

import scoda_engine_core as scoda_package
from scoda_engine.app import app
from scoda_engine_core import get_db, ScodaPackage, PackageRegistry

# Import release script functions
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))
from release import (
    get_version, get_artifact_id, get_artifact_name,
    calculate_sha256, store_sha256, get_statistics,
    get_provenance, build_metadata_json, generate_readme, create_release
)
from scoda_engine_core import validate_manifest, validate_db




# --- CORS ---

class TestCORS:
    def test_cors_headers_present(self, generic_client):
        """API responses should include CORS headers."""
        response = generic_client.get('/api/manifest', headers={"Origin": "http://localhost:3000"})
        assert response.status_code == 200
        assert 'access-control-allow-origin' in response.headers

    def test_cors_preflight(self, generic_client):
        """OPTIONS preflight requests should return CORS headers."""
        response = generic_client.options('/api/manifest', headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert 'access-control-allow-origin' in response.headers
        assert 'access-control-allow-methods' in response.headers
        assert 'GET' in response.headers['access-control-allow-methods']
        assert 'POST' in response.headers['access-control-allow-methods']


# --- MCP mount ---

class TestMCPMount:
    def test_mcp_health_via_mount(self, generic_client):
        """MCP health endpoint accessible through main app."""
        resp = generic_client.get("/mcp/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_mcp_messages_rejects_get(self, generic_client):
        """MCP messages endpoint should reject GET (POST only)."""
        resp = generic_client.get("/mcp/messages")
        assert resp.status_code == 405


# --- OpenAPI docs ---

class TestOpenAPIDocs:
    def test_openapi_json_contains_schemas(self, generic_client):
        """OpenAPI schema should contain Pydantic response model definitions."""
        response = generic_client.get('/openapi.json')
        assert response.status_code == 200
        schema = response.json()
        component_schemas = schema.get('components', {}).get('schemas', {})
        for model_name in ['ProvenanceItem', 'QueryResult', 'ManifestResponse',
                           'AnnotationItem', 'ErrorResponse']:
            assert model_name in component_schemas, f'{model_name} missing from OpenAPI schemas'


# --- Index page ---

class TestIndex:
    def test_index_returns_200(self, generic_client):
        response = generic_client.get('/')
        assert response.status_code == 200




# --- /api/provenance ---




# --- /api/provenance ---

class TestApiProvenance:
    def test_provenance_returns_200(self, generic_client):
        response = generic_client.get('/api/provenance')
        assert response.status_code == 200

    def test_provenance_returns_list(self, generic_client):
        response = generic_client.get('/api/provenance')
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_provenance_has_primary_source(self, generic_client):
        response = generic_client.get('/api/provenance')
        data = response.json()
        primary = next(s for s in data if s['source_type'] == 'primary')
        assert 'Test Source' in primary['citation']
        assert primary['year'] == 2024

    def test_provenance_has_supplementary_source(self, generic_client):
        response = generic_client.get('/api/provenance')
        data = response.json()
        supp = next(s for s in data if s['source_type'] == 'supplementary')
        assert 'Additional Source' in supp['citation']
        assert supp['year'] == 2025

    def test_provenance_record_structure(self, generic_client):
        response = generic_client.get('/api/provenance')
        data = response.json()
        record = data[0]
        expected_keys = ['id', 'source_type', 'citation', 'description', 'year', 'url']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"


# --- /api/display-intent ---




# --- /api/display-intent ---

class TestApiDisplayIntent:
    def test_display_intent_returns_200(self, generic_client):
        response = generic_client.get('/api/display-intent')
        assert response.status_code == 200

    def test_display_intent_returns_list(self, generic_client):
        response = generic_client.get('/api/display-intent')
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_display_intent_primary_view(self, generic_client):
        """items entity should have tree as primary (priority=0) view."""
        response = generic_client.get('/api/display-intent')
        data = response.json()
        items_intents = [i for i in data if i['entity'] == 'items']
        primary = next(i for i in items_intents if i['priority'] == 0)
        assert primary['default_view'] == 'tree'

    def test_display_intent_secondary_view(self, generic_client):
        """items entity should have table as secondary (priority=1) view."""
        response = generic_client.get('/api/display-intent')
        data = response.json()
        items_intents = [i for i in data if i['entity'] == 'items']
        secondary = next(i for i in items_intents if i['priority'] == 1)
        assert secondary['default_view'] == 'table'

    def test_display_intent_source_query(self, generic_client):
        response = generic_client.get('/api/display-intent')
        data = response.json()
        tree_intent = next(i for i in data if i['default_view'] == 'tree')
        assert tree_intent['source_query'] == 'category_tree'

    def test_display_intent_record_structure(self, generic_client):
        response = generic_client.get('/api/display-intent')
        data = response.json()
        record = data[0]
        expected_keys = ['id', 'entity', 'default_view', 'description',
                         'source_query', 'priority']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"


# --- /api/queries ---




# --- /api/queries ---

class TestApiQueries:
    def test_queries_returns_200(self, generic_client):
        response = generic_client.get('/api/queries')
        assert response.status_code == 200

    def test_queries_returns_list(self, generic_client):
        response = generic_client.get('/api/queries')
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 11

    def test_queries_record_structure(self, generic_client):
        response = generic_client.get('/api/queries')
        data = response.json()
        record = data[0]
        expected_keys = ['id', 'name', 'description', 'params', 'created_at']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"

    def test_queries_sorted_by_name(self, generic_client):
        response = generic_client.get('/api/queries')
        data = response.json()
        names = [q['name'] for q in data]
        assert names == sorted(names)


# --- /api/queries/<name>/execute ---




# --- /api/queries/<name>/execute ---

class TestApiQueryExecute:
    def test_execute_no_params(self, generic_client):
        """Execute items_list query (no parameters needed)."""
        response = generic_client.get('/api/queries/items_list/execute')
        assert response.status_code == 200
        data = response.json()
        assert data['query'] == 'items_list'
        assert data['row_count'] == 5  # 5 items in test data
        assert 'columns' in data
        assert 'rows' in data

    def test_execute_with_params(self, generic_client):
        """Execute category_items query with category_id parameter."""
        response = generic_client.get('/api/queries/category_items/execute?category_id=2')
        assert response.status_code == 200
        data = response.json()
        assert data['row_count'] == 2  # Relativity, Alchemy (both in Physics)
        names = [r['name'] for r in data['rows']]
        assert 'Relativity' in names

    def test_execute_results_sorted(self, generic_client):
        """items_list results should be sorted by name."""
        response = generic_client.get('/api/queries/items_list/execute')
        data = response.json()
        names = [r['name'] for r in data['rows']]
        assert names == sorted(names)

    def test_execute_not_found(self, generic_client):
        response = generic_client.get('/api/queries/nonexistent/execute')
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data

    def test_execute_columns_present(self, generic_client):
        """Result should include column names."""
        response = generic_client.get('/api/queries/items_list/execute')
        data = response.json()
        assert 'name' in data['columns']
        assert 'is_active' in data['columns']

    def test_execute_row_is_dict(self, generic_client):
        """Each row should be a dictionary with column keys."""
        response = generic_client.get('/api/queries/items_list/execute')
        data = response.json()
        row = data['rows'][0]
        assert isinstance(row, dict)
        assert 'name' in row


# --- /api/manifest ---




# --- /api/manifest ---

class TestApiManifest:
    def test_manifest_returns_200(self, generic_client):
        response = generic_client.get('/api/manifest')
        assert response.status_code == 200

    def test_manifest_returns_json(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert isinstance(data, dict)

    def test_manifest_has_name(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert data['name'] == 'default'

    def test_manifest_has_description(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert data['description'] == 'Test manifest'

    def test_manifest_has_created_at(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert 'created_at' in data
        assert data['created_at'] == '2026-02-20T00:00:00'

    def test_manifest_has_manifest_object(self, generic_client):
        """manifest_json should be parsed as an object, not returned as string."""
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert 'manifest' in data
        assert isinstance(data['manifest'], dict)

    def test_manifest_has_default_view(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert data['manifest']['default_view'] == 'category_tree'

    def test_manifest_has_views(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert 'views' in data['manifest']
        assert isinstance(data['manifest']['views'], dict)

    def test_manifest_view_count(self, generic_client):
        """Test manifest should have 4 views (2 tab + 2 detail)."""
        response = generic_client.get('/api/manifest')
        data = response.json()
        assert len(data['manifest']['views']) == 4

    def test_manifest_tree_view(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        tree = data['manifest']['views']['category_tree']
        assert tree['type'] == 'hierarchy'
        assert tree['display'] == 'tree'
        assert tree['source_query'] == 'category_tree'

    def test_manifest_table_view(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        table = data['manifest']['views']['items_table']
        assert table['type'] == 'table'
        assert table['source_query'] == 'items_list'

    def test_manifest_detail_view(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        detail = data['manifest']['views']['item_detail']
        assert detail['type'] == 'detail'

    def test_manifest_table_columns(self, generic_client):
        """Table views should have column definitions."""
        response = generic_client.get('/api/manifest')
        data = response.json()
        table = data['manifest']['views']['items_table']
        assert 'columns' in table
        assert isinstance(table['columns'], list)
        assert len(table['columns']) > 0
        col = table['columns'][0]
        assert 'key' in col
        assert 'label' in col

    def test_manifest_table_default_sort(self, generic_client):
        response = generic_client.get('/api/manifest')
        data = response.json()
        table = data['manifest']['views']['items_table']
        assert 'default_sort' in table
        assert table['default_sort']['key'] == 'name'
        assert table['default_sort']['direction'] == 'asc'

    def test_manifest_source_query_exists(self, generic_client):
        """source_query references should point to actual ui_queries entries."""
        response = generic_client.get('/api/manifest')
        data = response.json()

        queries_response = generic_client.get('/api/queries')
        queries_data = queries_response.json()
        query_names = {q['name'] for q in queries_data}

        for key, view in data['manifest']['views'].items():
            sq = view.get('source_query')
            if sq:
                assert sq in query_names, f"View '{key}' references query '{sq}' which doesn't exist"

    def test_manifest_response_structure(self, generic_client):
        """Top-level response should have exactly these keys."""
        response = generic_client.get('/api/manifest')
        data = response.json()
        expected_keys = ['name', 'description', 'manifest', 'created_at']
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


# --- Declarative Manifest Detail Views (Phase 39) ---




# --- Release Mechanism (Phase 16) ---

class TestRelease:
    def test_get_version(self, generic_db):
        """get_version should return '1.0.0' from test DB."""
        canonical_db, _ = generic_db
        assert get_version(canonical_db) == '1.0.0'

    def test_get_version_missing(self, tmp_path):
        """get_version should raise SystemExit when no version key exists."""
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        conn.close()
        with pytest.raises(SystemExit):
            get_version(db_path)

    def test_calculate_sha256(self, generic_db):
        """calculate_sha256 should return a 64-char hex string."""
        canonical_db, _ = generic_db
        h = calculate_sha256(canonical_db)
        assert len(h) == 64
        assert all(c in '0123456789abcdef' for c in h)

    def test_calculate_sha256_deterministic(self, generic_db):
        """Same file should always produce the same hash."""
        canonical_db, _ = generic_db
        h1 = calculate_sha256(canonical_db)
        h2 = calculate_sha256(canonical_db)
        assert h1 == h2

    def test_calculate_sha256_changes(self, generic_db):
        """Modifying the DB should change the hash."""
        canonical_db, _ = generic_db
        h_before = calculate_sha256(canonical_db)
        conn = sqlite3.connect(canonical_db)
        conn.execute("INSERT INTO artifact_metadata (key, value) VALUES ('test_key', 'test_value')")
        conn.commit()
        conn.close()
        h_after = calculate_sha256(canonical_db)
        assert h_before != h_after

    def test_store_sha256(self, generic_db):
        """store_sha256 should insert/update sha256 key in artifact_metadata."""
        canonical_db, _ = generic_db
        store_sha256(canonical_db, 'abc123def456')
        conn = sqlite3.connect(canonical_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM artifact_metadata WHERE key = 'sha256'"
        ).fetchone()
        conn.close()
        assert row['value'] == 'abc123def456'

    def test_get_statistics(self, generic_db):
        """get_statistics should return correct counts for test data (auto-discover)."""
        canonical_db, _ = generic_db
        stats = get_statistics(canonical_db)
        assert stats['items'] == 5
        assert stats['categories'] == 5
        assert stats['item_relations'] == 1
        assert stats['tags'] == 4
        assert stats['references'] == 3
        assert 'total_records' in stats

    def test_get_provenance(self, generic_db):
        """get_provenance should return 2 records with correct structure."""
        canonical_db, _ = generic_db
        prov = get_provenance(canonical_db)
        assert len(prov) == 2
        assert prov[0]['source_type'] == 'primary'
        assert 'Test Source' in prov[0]['citation']
        assert prov[1]['source_type'] == 'supplementary'
        for record in prov:
            assert 'id' in record
            assert 'citation' in record
            assert 'description' in record
            assert 'year' in record

    def test_build_metadata_json(self, generic_db):
        """build_metadata_json should include all required keys."""
        canonical_db, _ = generic_db
        meta = build_metadata_json(canonical_db, 'fakehash123')
        assert meta['artifact_id'] == 'sample-data'
        assert meta['version'] == '1.0.0'
        assert meta['sha256'] == 'fakehash123'
        assert 'released_at' in meta
        assert 'provenance' in meta
        assert isinstance(meta['provenance'], list)
        assert len(meta['provenance']) == 2
        assert 'statistics' in meta
        assert isinstance(meta['statistics'], dict)
        assert meta['statistics']['items'] == 5

    def test_generate_readme(self, generic_db):
        """generate_readme should include version, hash, and statistics."""
        canonical_db, _ = generic_db
        stats = get_statistics(canonical_db)
        readme = generate_readme('1.0.0', 'abc123hash', stats,
                                 artifact_id='sample-data', name='Sample Data')
        assert '1.0.0' in readme
        assert 'abc123hash' in readme
        assert 'items: 5' in readme
        assert 'categories: 5' in readme
        assert 'sha256sum --check' in readme
        assert 'Sample Data' in readme

    def test_create_release(self, generic_db, tmp_path):
        """Integration: create_release should produce directory with 4 files."""
        canonical_db, _ = generic_db
        output_dir = str(tmp_path / "releases")
        release_dir = create_release(canonical_db, output_dir)

        # Directory exists
        assert os.path.isdir(release_dir)
        assert 'sample-data-v1.0.0' in release_dir

        # 4 files exist
        assert os.path.isfile(os.path.join(release_dir, 'sample-data.db'))
        assert os.path.isfile(os.path.join(release_dir, 'metadata.json'))
        assert os.path.isfile(os.path.join(release_dir, 'checksums.sha256'))
        assert os.path.isfile(os.path.join(release_dir, 'README.md'))

        # DB is read-only
        db_stat = os.stat(os.path.join(release_dir, 'sample-data.db'))
        assert not (db_stat.st_mode & stat.S_IWUSR)
        assert not (db_stat.st_mode & stat.S_IWGRP)
        assert not (db_stat.st_mode & stat.S_IWOTH)

        # metadata.json is valid JSON with required keys
        with open(os.path.join(release_dir, 'metadata.json')) as f:
            meta = json.load(f)
        assert meta['version'] == '1.0.0'
        assert meta['artifact_id'] == 'sample-data'
        assert len(meta['sha256']) == 64

        # checksums.sha256 matches actual DB hash
        with open(os.path.join(release_dir, 'checksums.sha256')) as f:
            checksum_line = f.read().strip()
        recorded_hash = checksum_line.split('  ')[0]
        actual_hash = calculate_sha256(os.path.join(release_dir, 'sample-data.db'))
        assert recorded_hash == actual_hash

        # sha256 stored in source DB
        conn = sqlite3.connect(canonical_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT value FROM artifact_metadata WHERE key = 'sha256'"
        ).fetchone()
        conn.close()
        assert row['value'] == actual_hash

    def test_create_release_already_exists(self, generic_db, tmp_path):
        """Attempting to create a duplicate release should fail."""
        canonical_db, _ = generic_db
        output_dir = str(tmp_path / "releases")
        create_release(canonical_db, output_dir)
        with pytest.raises(SystemExit):
            create_release(canonical_db, output_dir)


# --- /api/annotations --- (Phase 17)




# --- /api/annotations --- (Phase 17)

class TestAnnotations:
    def test_get_annotations_empty(self, generic_client):
        """Entity with no annotations should return empty list."""
        response = generic_client.get('/api/annotations/item/1')
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_create_annotation(self, generic_client):
        """POST should create annotation and return 201."""
        response = generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'note',
                'content': 'This item needs revision.',
                'author': 'Test User'
            })
        assert response.status_code == 201
        data = response.json()
        assert data['entity_type'] == 'item'
        assert data['entity_id'] == 1
        assert data['annotation_type'] == 'note'
        assert data['content'] == 'This item needs revision.'
        assert data['author'] == 'Test User'

    def test_create_annotation_missing_content(self, generic_client):
        """POST without content should return 400."""
        response = generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'note'
            })
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data

    def test_get_annotations_after_create(self, generic_client):
        """GET after POST should return the created annotation."""
        generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'note',
                'content': 'Test note'
            })

        response = generic_client.get('/api/annotations/item/1')
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['content'] == 'Test note'

    def test_delete_annotation(self, generic_client):
        """DELETE should remove annotation and return 200."""
        create_resp = generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'note',
                'content': 'To be deleted'
            })
        annotation_id = create_resp.json()['id']

        response = generic_client.delete(f'/api/annotations/{annotation_id}')
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == annotation_id

        # Verify it's gone
        get_resp = generic_client.get('/api/annotations/item/1')
        assert get_resp.json() == []

    def test_delete_annotation_not_found(self, generic_client):
        """DELETE for non-existent ID should return 404."""
        response = generic_client.delete('/api/annotations/99999')
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data

    def test_annotations_ordered_by_date(self, generic_client):
        """Annotations should be returned newest first."""
        generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'note',
                'content': 'First note'
            })
        generic_client.post('/api/annotations',
            json={
                'entity_type': 'item',
                'entity_id': 1,
                'annotation_type': 'correction',
                'content': 'Second note'
            })

        response = generic_client.get('/api/annotations/item/1')
        data = response.json()
        assert len(data) == 2
        # Most recent first (both created in same second, so check by id desc)
        assert data[0]['content'] == 'Second note'
        assert data[1]['content'] == 'First note'

    def test_annotation_response_structure(self, generic_client):
        """Annotation response should have all required keys."""
        generic_client.post('/api/annotations',
            json={
                'entity_type': 'category',
                'entity_id': 2,
                'annotation_type': 'alternative',
                'content': 'May belong to different group',
                'author': 'Reviewer'
            })

        response = generic_client.get('/api/annotations/category/2')
        data = response.json()
        record = data[0]
        expected_keys = ['id', 'entity_type', 'entity_id', 'annotation_type',
                         'content', 'author', 'created_at']
        for key in expected_keys:
            assert key in record, f"Missing key: {key}"


# --- ScodaPackage (Phase 25) ---




# --- ScodaPackage (Phase 25) ---

class TestScodaPackage:
    def test_create_scoda(self, generic_db, tmp_path):
        """ScodaPackage.create should produce a valid .scoda ZIP."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        result = ScodaPackage.create(canonical_db, scoda_path)
        assert os.path.exists(result)
        assert zipfile.is_zipfile(result)

    def test_scoda_contains_manifest_and_db(self, generic_db, tmp_path):
        """The .scoda ZIP should contain manifest.json and data.db."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            names = zf.namelist()
            assert 'manifest.json' in names
            assert 'data.db' in names

    def test_scoda_manifest_fields(self, generic_db, tmp_path):
        """Manifest should contain required metadata fields."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            m = pkg.manifest
            assert m['format'] == 'scoda'
            assert m['format_version'] == '1.0'
            assert m['name'] == 'sample-data'
            assert m['version'] == '1.0.0'
            assert m['data_file'] == 'data.db'
            assert m['record_count'] > 0
            assert len(m['data_checksum_sha256']) == 64

    def test_scoda_open_and_read(self, generic_db, tmp_path):
        """Opening a .scoda package should extract DB and allow queries."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            conn = sqlite3.connect(pkg.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM items")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count > 0

    def test_scoda_checksum_verification(self, generic_db, tmp_path):
        """verify_checksum() should return True for unmodified package."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.verify_checksum() is True

    def test_scoda_close_cleanup(self, generic_db, tmp_path):
        """close() should remove the temp directory."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        pkg = ScodaPackage(scoda_path)
        tmp_dir = pkg._tmp_dir
        assert os.path.exists(tmp_dir)
        pkg.close()
        assert not os.path.exists(tmp_dir)

    def test_scoda_properties(self, generic_db, tmp_path):
        """Package properties should match manifest."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.version == '1.0.0'
            assert pkg.name == 'sample-data'
            assert pkg.record_count > 0

    def test_scoda_file_not_found(self, tmp_path):
        """Opening a nonexistent .scoda should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ScodaPackage(str(tmp_path / "nonexistent.scoda"))

    def test_get_db_with_testing_paths(self, generic_db):
        """get_db() with _set_paths_for_testing should work correctly."""
        canonical_db, overlay_db = generic_db
        scoda_package._set_paths_for_testing(canonical_db, overlay_db)
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM items")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count > 0
        finally:
            scoda_package._reset_paths()

    def test_get_db_overlay_attached(self, generic_db):
        """get_db() should have overlay DB attached."""
        canonical_db, overlay_db = generic_db
        scoda_package._set_paths_for_testing(canonical_db, overlay_db)
        try:
            conn = get_db()
            cursor = conn.cursor()
            # overlay.user_annotations should be accessible
            cursor.execute("SELECT COUNT(*) as cnt FROM overlay.user_annotations")
            count = cursor.fetchone()['cnt']
            conn.close()
            assert count == 0  # empty initially
        finally:
            scoda_package._reset_paths()


# --- PaleoCore .scoda Package (Phase 35) ---


# ---------------------------------------------------------------------------

class TestPackageRegistry:
    """Tests for PackageRegistry class."""

    def test_scan_finds_scoda_files(self, generic_db, tmp_path):
        """scan() should discover .scoda files in a directory."""
        canonical_db_path, overlay_db_path = generic_db

        # Create a .scoda package from the test DB
        pkg_dir = tmp_path / "pkg_scan"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        pkgs = reg.list_packages()
        assert len(pkgs) >= 1
        names = [p['name'] for p in pkgs]
        assert 'sample-data' in names
        reg.close_all()

    def test_open_package_db_connection(self, generic_db, tmp_path):
        """get_db() should return a working connection for a scanned package."""
        canonical_db_path, overlay_db_path = generic_db

        pkg_dir = tmp_path / "pkg_open"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('sample-data')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM items")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_list_packages_returns_info(self, generic_db, tmp_path):
        """list_packages() should return name, title, version, record_count."""
        canonical_db_path, overlay_db_path = generic_db

        pkg_dir = tmp_path / "pkg_list"
        pkg_dir.mkdir()
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "test.scoda"))

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        pkgs = reg.list_packages()
        assert len(pkgs) >= 1
        pkg = pkgs[0]
        assert 'name' in pkg
        assert 'title' in pkg
        assert 'version' in pkg
        assert 'record_count' in pkg
        assert 'has_dependencies' in pkg
        reg.close_all()

    def test_dependency_resolution_with_alias(self, generic_db, generic_dep_db, tmp_path):
        """Dependencies should be ATTACHed using their alias."""
        canonical_db_path, overlay_db_path = generic_db
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "pkg_deps"
        pkg_dir.mkdir()

        # Create dep-data.scoda
        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})

        # Create sample-data.scoda with dependency on dep-data
        ScodaPackage.create(canonical_db_path, str(pkg_dir / "sample-data.scoda"),
                            metadata={"dependencies": [
                                {"name": "dep-data", "alias": "dep"}
                            ]})

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('sample-data')
        # Verify dep alias is attached
        databases = conn.execute("PRAGMA database_list").fetchall()
        db_names = [row['name'] for row in databases]
        assert 'dep' in db_names

        # Verify cross-DB query works
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM dep.entries")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_package_without_deps(self, generic_dep_db, tmp_path):
        """A package with no dependencies should work standalone."""
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "pkg_nodeps"
        pkg_dir.mkdir()

        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('dep-data')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM entries")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()
        reg.close_all()

    def test_overlay_per_package(self, generic_db, generic_dep_db, tmp_path):
        """Each package should get its own overlay DB."""
        canonical_db_path, overlay_db_path = generic_db
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "pkg_overlay"
        pkg_dir.mkdir()

        ScodaPackage.create(canonical_db_path, str(pkg_dir / "sample-data.scoda"))
        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        # Open both — each creates its own overlay
        conn1 = reg.get_db('sample-data')
        conn2 = reg.get_db('dep-data')

        assert os.path.exists(str(pkg_dir / "sample-data_overlay.db"))
        assert os.path.exists(str(pkg_dir / "dep-data_overlay.db"))

        conn1.close()
        conn2.close()
        reg.close_all()

    def test_legacy_get_db_still_works(self, generic_db):
        """Existing get_db() function should continue to work."""
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)

        conn = scoda_package.get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM items")
        count = cursor.fetchone()['cnt']
        assert count > 0
        conn.close()

        scoda_package._reset_paths()

    def test_unknown_package_error(self, tmp_path):
        """get_db() for a non-existent package should raise KeyError."""
        pkg_dir = tmp_path / "pkg_err"
        pkg_dir.mkdir()

        from scoda_engine_core import PackageRegistry
        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        with pytest.raises(KeyError):
            reg.get_db('nonexistent')
        reg.close_all()


# ---------------------------------------------------------------------------
# /api/detail/<query_name> endpoint tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestGenericDetailEndpoint:
    """Tests for /api/detail/<query_name> generic detail endpoint."""

    def test_detail_returns_first_row(self, generic_client):
        """GET /api/detail/<query> should return first row as flat JSON."""
        response = generic_client.get('/api/detail/items_list')
        assert response.status_code == 200
        data = response.json()
        # Should be a flat dict (first row), not wrapped in rows/columns
        assert 'name' in data
        assert 'rows' not in data

    def test_detail_with_params(self, generic_client):
        """GET /api/detail/<query>?param=value should pass parameters."""
        response = generic_client.get('/api/detail/items_list')
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_detail_query_not_found(self, generic_client):
        """Non-existent query should return 404."""
        response = generic_client.get('/api/detail/nonexistent_query')
        assert response.status_code == 404
        data = response.json()
        assert 'error' in data

    def test_detail_no_results(self, generic_client):
        """Query returning 0 rows should return 404."""
        response = generic_client.get('/api/detail/category_items?category_id=999999')
        assert response.status_code == 404
        data = response.json()
        assert data['error'] == 'Not found'

    def test_detail_nonexistent_query(self, generic_client):
        """Non-existent query should return 404."""
        response = generic_client.get('/api/detail/nonexistent_query')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# set_active_package() integration tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestActivePackage:
    """Tests for set_active_package() integration with get_db()."""

    def test_set_active_package_routes_get_db(self, generic_db, tmp_path):
        """set_active_package() should make get_db() use registry."""
        canonical_db_path, overlay_db_path = generic_db
        import scoda_engine_core.scoda_package as sp_mod
        from scoda_engine_core import PackageRegistry

        pkg_dir = str(tmp_path / "active_pkg")
        os.makedirs(pkg_dir, exist_ok=True)
        ScodaPackage.create(canonical_db_path, os.path.join(pkg_dir, "sample-data.scoda"))

        old_registry = sp_mod._registry
        sp_mod._registry = PackageRegistry()
        sp_mod._registry.scan(pkg_dir)

        try:
            sp_mod.set_active_package('sample-data')
            conn = sp_mod.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM items")
            count = cursor.fetchone()['cnt']
            assert count > 0
            conn.close()
        finally:
            sp_mod._active_package_name = None
            sp_mod._registry.close_all()
            sp_mod._registry = old_registry

    def test_active_package_cleared_by_testing(self, generic_db):
        """_set_paths_for_testing() should clear active package."""
        import scoda_engine_core.scoda_package as sp_mod
        sp_mod._active_package_name = 'something'
        canonical_db_path, overlay_db_path = generic_db
        sp_mod._set_paths_for_testing(canonical_db_path, overlay_db_path)
        assert sp_mod._active_package_name is None
        sp_mod._reset_paths()


# ---------------------------------------------------------------------------
# Phase 44: Reference SPA tests
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------

class TestScodaPackageSPA:
    """Tests for Reference SPA features in ScodaPackage."""

    def test_create_with_spa(self, generic_db, tmp_path):
        """extra_assets should be included in .scoda ZIP."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        # Create a fake SPA file
        spa_file = tmp_path / "test_app.js"
        spa_file.write_text("console.log('spa');")

        extra_assets = {"assets/spa/app.js": str(spa_file)}
        ScodaPackage.create(canonical_db, scoda_path, extra_assets=extra_assets)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            names = zf.namelist()
            assert 'assets/spa/app.js' in names

    def test_has_reference_spa(self, generic_db, tmp_path):
        """has_reference_spa should reflect manifest flag."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test_spa.scoda")

        spa_file = tmp_path / "index.html"
        spa_file.write_text("<html></html>")

        extra_assets = {"assets/spa/index.html": str(spa_file)}
        metadata = {"has_reference_spa": True, "reference_spa_path": "assets/spa/"}
        ScodaPackage.create(canonical_db, scoda_path, metadata=metadata,
                           extra_assets=extra_assets)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.has_reference_spa is True

    def test_has_reference_spa_false_by_default(self, generic_db, tmp_path):
        """has_reference_spa should be False when not set."""
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "test_no_spa.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.has_reference_spa is False






class TestGenericViewer:
    """Tests for generic viewer serving."""

    def test_index_serves_generic_viewer(self, generic_client):
        """Index should serve generic viewer."""
        response = generic_client.get('/')
        assert response.status_code == 200
        html = response.text
        assert 'SCODA Desktop' in html





# --- /api/composite/<view_name> ---


class TestCompositeDetail:
    """Tests for /api/composite/<view_name> manifest-driven composite endpoint."""

    def test_composite_requires_id(self, generic_client):
        """Missing id parameter should return 400."""
        response = generic_client.get('/api/composite/item_detail')
        assert response.status_code == 400
        data = response.json()
        assert 'id parameter required' in data['error']

    def test_composite_unknown_view_returns_404(self, generic_client):
        """Non-existent view name should return 404."""
        response = generic_client.get('/api/composite/nonexistent_view?id=1')
        assert response.status_code == 404
        data = response.json()
        assert 'Detail view not found' in data['error']

    def test_composite_non_detail_view_returns_404(self, generic_client):
        """Table view (not detail type) should return 404."""
        response = generic_client.get('/api/composite/items_table?id=1')
        assert response.status_code == 404

    def test_composite_hierarchy_view_returns_404(self, generic_client):
        """Hierarchy view (not detail type) should return 404."""
        response = generic_client.get('/api/composite/category_tree?id=1')
        assert response.status_code == 404

    def test_composite_entity_not_found(self, generic_client):
        """Non-existent entity id should return 404."""
        response = generic_client.get('/api/composite/item_detail?id=999999')
        assert response.status_code == 404

    def test_composite_item_returns_main_data(self, generic_client):
        """Composite item detail should return main query fields at top level."""
        response = generic_client.get('/api/composite/item_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Gravity'
        assert data['category_name'] == 'Mechanics'
        assert data['author'] == 'Newton'

    def test_composite_item_has_sub_query_keys(self, generic_client):
        """Composite item detail should include sub-query result arrays."""
        response = generic_client.get('/api/composite/item_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert 'hierarchy' in data
        assert 'relations' in data
        assert 'tags' in data
        assert 'related_items' in data
        assert isinstance(data['hierarchy'], list)
        assert isinstance(data['relations'], list)

    def test_composite_item_hierarchy(self, generic_client):
        """Hierarchy should walk up from item's category to root."""
        response = generic_client.get('/api/composite/item_detail?id=1')
        data = response.json()
        hierarchy = data['hierarchy']
        assert len(hierarchy) >= 2  # At least group and root
        # Should be ordered root -> group -> subgroup (top to bottom)
        levels = [h['level'] for h in hierarchy]
        assert levels[0] == 'root'
        assert 'subgroup' in levels

    def test_composite_item_relations_empty(self, generic_client):
        """Item with no relations should have empty list."""
        response = generic_client.get('/api/composite/item_detail?id=1')
        data = response.json()
        assert data['relations'] == []

    def test_composite_item_tags(self, generic_client):
        """Item with tags should list them."""
        response = generic_client.get('/api/composite/item_detail?id=1')
        data = response.json()
        assert len(data['tags']) == 2  # 'classical', 'fundamental'
        tag_names = [t['tag_name'] for t in data['tags']]
        assert 'classical' in tag_names

    def test_composite_item_relations(self, generic_client):
        """Item with relations should list them."""
        response = generic_client.get('/api/composite/item_detail?id=5')
        data = response.json()
        assert len(data['relations']) == 1
        assert data['relations'][0]['target_name'] == 'Relativity'

    def test_composite_result_field_param(self, generic_client):
        """Sub-query using result.field should resolve from main query result."""
        # related_items uses result.category_id
        response = generic_client.get('/api/composite/item_detail?id=2')
        data = response.json()
        # Relativity has category_id=2 (Physics), which also contains Alchemy
        assert 'related_items' in data
        assert isinstance(data['related_items'], list)
        assert len(data['related_items']) == 2  # Relativity and Alchemy
        names = [r['name'] for r in data['related_items']]
        assert 'Alchemy' in names

    def test_composite_category_detail(self, generic_client):
        """Composite category detail should return main + children + counts."""
        response = generic_client.get('/api/composite/category_detail?id=1')
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Science'
        assert 'children' in data
        assert 'children_counts' in data
        assert isinstance(data['children'], list)
        assert isinstance(data['children_counts'], list)


class TestGenericViewerFallback:
    """Tests for generic viewer graceful handling of unknown section types."""

    def test_index_serves_html(self, generic_client):
        """Generic viewer should serve valid HTML."""
        response = generic_client.get('/')
        assert response.status_code == 200
        html = response.text
        assert '<html' in html
        assert 'SCODA Desktop' in html

    def test_spa_404_for_nonexistent_files(self, generic_client):
        """Requests for non-existent SPA files should return 404."""
        response = generic_client.get('/nonexistent.js')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Phase 46 Step 2: Dynamic MCP Tool Loading
# ---------------------------------------------------------------------------

class TestDynamicMcpTools:
    """Tests for dynamic MCP tool loading from .scoda packages."""

    # --- ScodaPackage mcp_tools property ---

    def test_scoda_package_mcp_tools_property(self, generic_scoda_with_mcp_tools):
        """ScodaPackage.mcp_tools should return parsed dict when mcp_tools.json is present."""
        scoda_path, _, _ = generic_scoda_with_mcp_tools
        with ScodaPackage(scoda_path) as pkg:
            tools = pkg.mcp_tools
            assert tools is not None
            assert tools['format_version'] == '1.0'
            assert len(tools['tools']) == 3

    def test_scoda_package_no_mcp_tools(self, generic_db, tmp_path):
        """ScodaPackage.mcp_tools should return None when no mcp_tools.json."""
        canonical_db_path, _ = generic_db
        output = str(tmp_path / "no_mcp.scoda")
        ScodaPackage.create(canonical_db_path, output)
        with ScodaPackage(output) as pkg:
            assert pkg.mcp_tools is None

    def test_scoda_create_with_mcp_tools(self, generic_scoda_with_mcp_tools):
        """ScodaPackage.create() with mcp_tools_path should include mcp_tools.json in ZIP."""
        scoda_path, _, _ = generic_scoda_with_mcp_tools
        import zipfile
        with zipfile.ZipFile(scoda_path, 'r') as zf:
            assert 'mcp_tools.json' in zf.namelist()

    # --- SQL validation ---

    def test_validate_sql_select_allowed(self):
        """SELECT statements should pass validation."""
        from scoda_engine.mcp_server import _validate_sql
        _validate_sql("SELECT id, name FROM items")

    def test_validate_sql_with_allowed(self):
        """WITH (CTE) statements should pass validation."""
        from scoda_engine.mcp_server import _validate_sql
        _validate_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")

    def test_validate_sql_insert_rejected(self):
        """INSERT statements should be rejected."""
        from scoda_engine.mcp_server import _validate_sql
        import pytest
        with pytest.raises(ValueError, match="Forbidden SQL keyword"):
            _validate_sql("SELECT 1; INSERT INTO foo VALUES (1)")

    def test_validate_sql_drop_rejected(self):
        """DROP statements should be rejected."""
        from scoda_engine.mcp_server import _validate_sql
        import pytest
        with pytest.raises(ValueError, match="Forbidden SQL keyword"):
            _validate_sql("SELECT 1; DROP TABLE foo")

    def test_validate_sql_update_rejected(self):
        """UPDATE statements should be rejected."""
        from scoda_engine.mcp_server import _validate_sql
        import pytest
        with pytest.raises(ValueError, match="Forbidden SQL keyword"):
            _validate_sql("SELECT 1; UPDATE foo SET x=1")

    def test_validate_sql_delete_rejected(self):
        """DELETE statements should be rejected."""
        from scoda_engine.mcp_server import _validate_sql
        import pytest
        with pytest.raises(ValueError, match="Forbidden SQL keyword"):
            _validate_sql("SELECT 1; DELETE FROM foo")

    def test_validate_sql_non_select_rejected(self):
        """Non-SELECT/WITH starting SQL should be rejected."""
        from scoda_engine.mcp_server import _validate_sql
        import pytest
        with pytest.raises(ValueError, match="SQL must start with SELECT or WITH"):
            _validate_sql("PRAGMA table_info(foo)")

    # --- Dynamic tool execution ---

    def test_dynamic_tool_single_query(self, generic_db):
        """Dynamic tool with query_type='single' should execute SQL and return results."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {
                "query_type": "single",
                "sql": "SELECT id, name FROM items WHERE name LIKE :pattern ORDER BY name LIMIT :limit",
                "default_params": {"limit": 10}
            }
            result = _execute_dynamic_tool(tool_def, {"pattern": "Grav%"})
            assert 'rows' in result
            assert result['row_count'] >= 1
            names = [r['name'] for r in result['rows']]
            assert 'Gravity' in names
        finally:
            scoda_package._reset_paths()

    def test_dynamic_tool_named_query(self, generic_db):
        """Dynamic tool with query_type='named_query' should execute named query."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {
                "query_type": "named_query",
                "named_query": "category_tree",
                "param_mapping": {}
            }
            result = _execute_dynamic_tool(tool_def, {})
            assert 'rows' in result
            assert result['row_count'] >= 1
        finally:
            scoda_package._reset_paths()

    def test_dynamic_tool_named_query_with_params(self, generic_db):
        """Dynamic tool with query_type='named_query' should pass mapped params."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {
                "query_type": "named_query",
                "named_query": "category_items",
                "param_mapping": {"category_id": "category_id"}
            }
            result = _execute_dynamic_tool(tool_def, {"category_id": 2})
            assert 'rows' in result
            # Physics (id=2) has items (Relativity, Alchemy)
            assert result['row_count'] >= 1
        finally:
            scoda_package._reset_paths()

    def test_dynamic_tool_composite(self, generic_db):
        """Dynamic tool with query_type='composite' should execute composite detail."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {
                "query_type": "composite",
                "view_name": "item_detail",
                "param_mapping": {"item_id": "item_id"}
            }
            result = _execute_dynamic_tool(tool_def, {"item_id": 1})
            assert 'name' in result
            assert result['name'] == 'Gravity'
            # Composite should include sub-query results
            assert 'relations' in result
            assert 'tags' in result
        finally:
            scoda_package._reset_paths()

    def test_dynamic_tool_default_params(self, generic_db):
        """Dynamic tool should merge default_params with provided arguments."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {
                "query_type": "single",
                "sql": "SELECT id, name FROM items WHERE is_active = 1 AND name LIKE :pattern LIMIT :limit",
                "default_params": {"limit": 2}
            }
            result = _execute_dynamic_tool(tool_def, {"pattern": "%"})
            assert result['row_count'] <= 2
        finally:
            scoda_package._reset_paths()

    def test_dynamic_tool_unknown_query_type(self, generic_db):
        """Dynamic tool with unknown query_type should return error."""
        from scoda_engine.mcp_server import _execute_dynamic_tool
        canonical_db_path, overlay_db_path = generic_db
        scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
        try:
            tool_def = {"query_type": "unknown"}
            result = _execute_dynamic_tool(tool_def, {})
            assert 'error' in result
        finally:
            scoda_package._reset_paths()

    # --- Built-in tools always present ---

    def test_builtin_tools_always_present(self):
        """Built-in tools should always be returned."""
        from scoda_engine.mcp_server import _get_builtin_tools, _BUILTIN_TOOL_NAMES
        tools = _get_builtin_tools()
        tool_names = {t.name for t in tools}
        assert tool_names == _BUILTIN_TOOL_NAMES
        assert len(tools) == 7

    def test_dynamic_tools_from_mcp_tools_json(self, generic_mcp_tools_data):
        """_get_dynamic_tools should create Tool objects from mcp_tools data."""
        from scoda_engine.mcp_server import _get_dynamic_tools
        from unittest.mock import patch

        with patch('scoda_engine.mcp_server.get_mcp_tools', return_value=generic_mcp_tools_data):
            tools = _get_dynamic_tools()
            assert len(tools) == 3
            names = {t.name for t in tools}
            assert names == {'test_search', 'test_tree', 'test_item_detail'}

    def test_dynamic_tools_empty_when_no_mcp_tools(self):
        """_get_dynamic_tools should return [] when get_mcp_tools() returns None."""
        from scoda_engine.mcp_server import _get_dynamic_tools
        from unittest.mock import patch

        with patch('scoda_engine.mcp_server.get_mcp_tools', return_value=None):
            tools = _get_dynamic_tools()
            assert tools == []

    # --- Registry get_mcp_tools ---

    def test_registry_get_mcp_tools(self, generic_scoda_with_mcp_tools, tmp_path):
        """PackageRegistry.get_mcp_tools should return tools from .scoda package."""
        from scoda_engine_core import PackageRegistry
        scoda_path, _, _ = generic_scoda_with_mcp_tools

        registry = PackageRegistry()
        # Manually register the package
        pkg = ScodaPackage(scoda_path)
        registry._packages[pkg.name] = {
            'pkg': pkg,
            'db_path': pkg.db_path,
            'overlay_path': str(tmp_path / 'overlay.db'),
            'deps': [],
        }

        tools = registry.get_mcp_tools(pkg.name)
        assert tools is not None
        assert len(tools['tools']) == 3
        pkg.close()

    def test_registry_get_mcp_tools_not_found(self):
        """PackageRegistry.get_mcp_tools should return None for unknown package."""
        from scoda_engine_core import PackageRegistry
        registry = PackageRegistry()
        assert registry.get_mcp_tools('nonexistent') is None

    # --- Module-level get_mcp_tools ---

    def test_module_get_mcp_tools_with_scoda(self, generic_scoda_with_mcp_tools, tmp_path):
        """Module-level get_mcp_tools should work via legacy _scoda_pkg path."""
        import scoda_engine_core.scoda_package as sp_mod
        from scoda_engine_core import get_mcp_tools as module_get_mcp_tools
        scoda_path, canonical, overlay = generic_scoda_with_mcp_tools

        # Open .scoda and set it as the module-level _scoda_pkg
        pkg = ScodaPackage(scoda_path)
        old_pkg = sp_mod._scoda_pkg
        old_canonical = sp_mod._canonical_db
        try:
            sp_mod._scoda_pkg = pkg
            sp_mod._canonical_db = pkg.db_path  # ensure _resolve_paths won't re-resolve
            sp_mod._active_package_name = None
            tools = module_get_mcp_tools()
            assert tools is not None
            assert len(tools['tools']) == 3
        finally:
            sp_mod._scoda_pkg = old_pkg
            sp_mod._canonical_db = old_canonical
            pkg.close()


# --- UID Schema (Phase A) ---

class TestUIDSchema:
    """Tests for SCODA Stable UID columns and values."""

    def test_canonical_uid_columns_exist(self, generic_db):
        """categories and items should have uid, uid_method, uid_confidence, same_as_uid columns."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        for table in ['categories', 'items']:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            for col in ['uid', 'uid_method', 'uid_confidence', 'same_as_uid']:
                assert col in cols, f"{table} missing column: {col}"
        conn.close()

    def test_dep_uid_columns_exist(self, generic_dep_db):
        """Dependency tables should have uid columns."""
        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations', 'time_periods', 'entries']:
            cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            for col in ['uid', 'uid_method', 'uid_confidence', 'same_as_uid']:
                assert col in cols, f"{table} missing column: {col}"
        conn.close()

    def test_uid_unique_constraint_canonical(self, generic_db):
        """categories.uid and items.uid should have UNIQUE constraint."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        for table in ['categories', 'items']:
            indexes = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table}' AND name LIKE '%uid%'"
            ).fetchall()
            uid_index_sqls = [r[0] for r in indexes if r[0]]
            assert any('UNIQUE' in sql for sql in uid_index_sqls), f"No UNIQUE index on {table}.uid"
        conn.close()

    def test_uid_unique_constraint_dep(self, generic_dep_db):
        """Dependency uid columns should have UNIQUE constraints."""
        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations', 'time_periods', 'entries']:
            indexes = conn.execute(
                f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table}' AND name LIKE '%uid%'"
            ).fetchall()
            uid_index_sqls = [r[0] for r in indexes if r[0]]
            assert any('UNIQUE' in sql for sql in uid_index_sqls), \
                f"No UNIQUE index on {table}.uid"
        conn.close()

    def test_uid_format_scoda_prefix(self, generic_db, generic_dep_db):
        """All UIDs should start with 'scoda:' prefix."""
        canonical_db_path, _ = generic_db
        # Check canonical tables
        conn = sqlite3.connect(canonical_db_path)
        for table in ['categories', 'items']:
            uids = conn.execute(
                f"SELECT uid FROM {table} WHERE uid IS NOT NULL"
            ).fetchall()
            for (uid,) in uids:
                assert uid.startswith('scoda:'), f"Bad UID prefix in {table}: {uid}"
        conn.close()

        # Check dep tables
        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations', 'time_periods', 'entries']:
            uids = conn.execute(
                f"SELECT uid FROM {table} WHERE uid IS NOT NULL"
            ).fetchall()
            for (uid,) in uids:
                assert uid.startswith('scoda:'), f"Bad UID prefix in {table}: {uid}"
        conn.close()

    def test_uid_format_categories(self, generic_db):
        """categories UIDs should follow scoda:cat:<level>:<name> format."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        rows = conn.execute(
            "SELECT name, level, uid FROM categories WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        for name, level, uid in rows:
            assert uid == f"scoda:cat:{level}:{name}", \
                f"Bad UID format: {uid} for {level} {name}"

    def test_uid_format_items(self, generic_db):
        """items UIDs should follow scoda:item:name:<name> format."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        rows = conn.execute(
            "SELECT name, uid FROM items WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        for name, uid in rows:
            assert uid == f"scoda:item:name:{name}", \
                f"Bad UID format: {uid} for {name}"

    def test_uid_format_time_periods(self, generic_dep_db):
        """time_periods UIDs should follow scoda:data:period:code:<code> format."""
        conn = sqlite3.connect(generic_dep_db)
        rows = conn.execute(
            "SELECT code, uid FROM time_periods WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        for code, uid in rows:
            assert uid == f"scoda:data:period:code:{code}", \
                f"Bad UID: {uid} for {code}"

    def test_uid_format_regions(self, generic_dep_db):
        """regions UIDs should follow scoda:data:region:code:<code> format."""
        conn = sqlite3.connect(generic_dep_db)
        rows = conn.execute(
            "SELECT uid, uid_method FROM regions WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        for uid, method in rows:
            if method == 'code':
                assert uid.startswith('scoda:data:region:code:'), f"Bad region UID: {uid}"

    def test_uid_format_locations(self, generic_dep_db):
        """locations UIDs should match expected patterns by level."""
        conn = sqlite3.connect(generic_dep_db)
        rows = conn.execute(
            "SELECT uid, uid_method, level FROM locations WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        for uid, method, level in rows:
            if level == 'region':
                assert uid.startswith('scoda:data:region:'), f"Bad region UID: {uid}"
            elif level == 'subregion':
                assert uid.startswith('scoda:data:location:'), f"Bad subregion UID: {uid}"

    def test_uid_no_nulls(self, generic_db, generic_dep_db):
        """All tables should have zero NULL UIDs."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        for table in ['categories', 'items']:
            null_count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE uid IS NULL"
            ).fetchone()[0]
            assert null_count == 0, f"{table} has {null_count} NULL UIDs"
        conn.close()

        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations', 'time_periods', 'entries']:
            null_count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE uid IS NULL"
            ).fetchone()[0]
            assert null_count == 0, f"{table} has {null_count} NULL UIDs"
        conn.close()

    def test_uid_confidence_values(self, generic_db, generic_dep_db):
        """uid_confidence should only contain valid values."""
        valid = {'high', 'medium', 'low'}
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        for table in ['categories', 'items']:
            values = conn.execute(
                f"SELECT DISTINCT uid_confidence FROM {table} WHERE uid_confidence IS NOT NULL"
            ).fetchall()
            for (val,) in values:
                assert val in valid, f"Invalid confidence in {table}: {val}"
        conn.close()

        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations', 'time_periods', 'entries']:
            values = conn.execute(
                f"SELECT DISTINCT uid_confidence FROM {table} WHERE uid_confidence IS NOT NULL"
            ).fetchall()
            for (val,) in values:
                assert val in valid, f"Invalid confidence in {table}: {val}"
        conn.close()


class TestUIDPhaseB:
    """Phase B UID quality: region-level locations ↔ regions consistency, same_as_uid."""

    def test_region_level_locations_matches_regions(self, generic_dep_db):
        """Region-level locations UIDs should match regions table UIDs."""
        conn = sqlite3.connect(generic_dep_db)
        mismatches = conn.execute("""
            SELECT COUNT(*) FROM locations loc
            JOIN regions r ON loc.name = r.name
            WHERE loc.level = 'region' AND loc.uid != r.uid
        """).fetchone()[0]
        conn.close()
        assert mismatches == 0, f"Found {mismatches} region-level locations ↔ regions UID mismatches"

    def test_no_collision_suffixes(self, generic_dep_db):
        """No UIDs should have collision suffixes like -2, -3."""
        conn = sqlite3.connect(generic_dep_db)
        for table in ['regions', 'locations']:
            collisions = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE uid LIKE '%-_' AND uid_method != 'fp_v1'"
            ).fetchone()[0]
            assert collisions == 0, f"Found {collisions} collision suffixes in {table}"
        conn.close()

    def test_same_as_uid_references_valid_uid(self, generic_dep_db):
        """same_as_uid should reference an existing uid in the same table."""
        conn = sqlite3.connect(generic_dep_db)
        # Check locations same_as_uid references
        rows = conn.execute(
            "SELECT id, same_as_uid FROM locations WHERE same_as_uid IS NOT NULL"
        ).fetchall()
        for row_id, same_as in rows:
            target = conn.execute(
                "SELECT COUNT(*) FROM locations WHERE uid = ?", (same_as,)
            ).fetchone()[0]
            assert target > 0, f"locations id={row_id} same_as_uid references non-existent uid: {same_as}"
        conn.close()

    def test_code_primary_is_actual_region(self, generic_dep_db):
        """code-method UIDs should belong to actual region names, not sub-locations."""
        conn = sqlite3.connect(generic_dep_db)
        # Sub-location names that should NOT be code-method primary
        sub_locations = ['Western Europe', 'East Asia']
        for name in sub_locations:
            row = conn.execute(
                "SELECT uid_method FROM regions WHERE name = ?", (name,)
            ).fetchone()
            if row:
                assert row[0] != 'code', f"{name} should not be code-method primary in regions"
        conn.close()


class TestUIDPhaseC:
    """Phase C UID: references and entries uid columns, format, coverage."""

    def test_references_uid_columns_exist(self, generic_db):
        """references should have uid, uid_method, uid_confidence, same_as_uid columns."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        cols = [r[1] for r in conn.execute('PRAGMA table_info("references")').fetchall()]
        conn.close()
        for col in ['uid', 'uid_method', 'uid_confidence', 'same_as_uid']:
            assert col in cols, f"Missing column: {col}"

    def test_references_uid_unique_index(self, generic_db):
        """references.uid should have UNIQUE constraint."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        indexes = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='references' AND name LIKE '%uid%'"
        ).fetchall()
        conn.close()
        uid_index_sqls = [r[0] for r in indexes if r[0]]
        assert any('UNIQUE' in sql for sql in uid_index_sqls), "No UNIQUE index on references.uid"

    def test_entries_uid_columns_exist(self, generic_dep_db):
        """entries should have uid, uid_method, uid_confidence, same_as_uid columns."""
        conn = sqlite3.connect(generic_dep_db)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
        conn.close()
        for col in ['uid', 'uid_method', 'uid_confidence', 'same_as_uid']:
            assert col in cols, f"Missing column: {col}"

    def test_entries_uid_unique_index(self, generic_dep_db):
        """entries.uid should have UNIQUE constraint."""
        conn = sqlite3.connect(generic_dep_db)
        indexes = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='entries' AND name LIKE '%uid%'"
        ).fetchall()
        conn.close()
        uid_index_sqls = [r[0] for r in indexes if r[0]]
        assert any('UNIQUE' in sql for sql in uid_index_sqls), "No UNIQUE index on entries.uid"

    def test_references_uid_format(self, generic_db):
        """references UIDs should start with scoda:ref: prefix."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        uids = conn.execute(
            'SELECT uid FROM "references" WHERE uid IS NOT NULL'
        ).fetchall()
        conn.close()
        assert len(uids) > 0, "No references UIDs found"
        for (uid,) in uids:
            assert uid.startswith('scoda:ref:'), f"Bad references UID prefix: {uid}"

    def test_entries_uid_format(self, generic_dep_db):
        """entries UIDs should start with scoda:data:entry: prefix."""
        conn = sqlite3.connect(generic_dep_db)
        uids = conn.execute(
            "SELECT uid FROM entries WHERE uid IS NOT NULL"
        ).fetchall()
        conn.close()
        assert len(uids) > 0, "No entries UIDs found"
        for (uid,) in uids:
            assert uid.startswith('scoda:data:entry:'), f"Bad entries UID prefix: {uid}"

    def test_references_no_null_uids(self, generic_db):
        """All references records should have UIDs (100% coverage)."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        null_count = conn.execute(
            'SELECT COUNT(*) FROM "references" WHERE uid IS NULL'
        ).fetchone()[0]
        conn.close()
        assert null_count == 0, f"references has {null_count} NULL UIDs"

    def test_entries_no_null_uids(self, generic_dep_db):
        """All entries records should have UIDs (100% coverage)."""
        conn = sqlite3.connect(generic_dep_db)
        null_count = conn.execute(
            "SELECT COUNT(*) FROM entries WHERE uid IS NULL"
        ).fetchone()[0]
        conn.close()
        assert null_count == 0, f"entries has {null_count} NULL UIDs"

    def test_references_confidence_values(self, generic_db):
        """references uid_confidence should only be high, medium, or low."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        values = conn.execute(
            'SELECT DISTINCT uid_confidence FROM "references" WHERE uid_confidence IS NOT NULL'
        ).fetchall()
        conn.close()
        valid = {'high', 'medium', 'low'}
        for (val,) in values:
            assert val in valid, f"Invalid references confidence: {val}"

    def test_cross_ref_low_confidence(self, generic_db):
        """cross_ref references entries should have low confidence."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        rows = conn.execute(
            'SELECT uid_confidence FROM "references" WHERE reference_type = \'cross_ref\''
        ).fetchall()
        conn.close()
        for (conf,) in rows:
            assert conf == 'low', f"cross_ref should have low confidence, got: {conf}"

    def test_references_doi_uid_format(self, generic_db):
        """DOI-upgraded references UIDs should use scoda:ref:doi: prefix with high confidence."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        rows = conn.execute(
            'SELECT uid, uid_method, uid_confidence FROM "references" WHERE uid_method = \'doi\''
        ).fetchall()
        conn.close()
        assert len(rows) > 0, "No DOI-method references records found"
        for uid, method, conf in rows:
            assert uid.startswith('scoda:ref:doi:'), f"DOI uid should start with scoda:ref:doi:, got: {uid}"
            assert conf == 'high', f"DOI confidence should be high, got: {conf}"

    def test_entries_lexicon_uid_format(self, generic_dep_db):
        """Lexicon-upgraded entries UIDs should use scoda:data:entry:lexicon: prefix with high confidence."""
        conn = sqlite3.connect(generic_dep_db)
        rows = conn.execute(
            "SELECT uid, uid_method, uid_confidence FROM entries WHERE uid_method = 'lexicon'"
        ).fetchall()
        conn.close()
        assert len(rows) > 0, "No lexicon-method entry records found"
        for uid, method, conf in rows:
            assert uid.startswith('scoda:data:entry:lexicon:'), f"Lexicon uid should start with scoda:data:entry:lexicon:, got: {uid}"
            assert conf == 'high', f"Lexicon confidence should be high, got: {conf}"

    def test_references_uid_methods_valid(self, generic_db):
        """references uid_method should only be fp_v1 or doi."""
        canonical_db_path, _ = generic_db
        conn = sqlite3.connect(canonical_db_path)
        methods = conn.execute(
            'SELECT DISTINCT uid_method FROM "references" WHERE uid_method IS NOT NULL'
        ).fetchall()
        conn.close()
        valid = {'fp_v1', 'doi'}
        for (m,) in methods:
            assert m in valid, f"Invalid references uid_method: {m}"

    def test_entries_uid_methods_valid(self, generic_dep_db):
        """entries uid_method should only be fp_v1 or lexicon."""
        conn = sqlite3.connect(generic_dep_db)
        methods = conn.execute(
            "SELECT DISTINCT uid_method FROM entries WHERE uid_method IS NOT NULL"
        ).fetchall()
        conn.close()
        valid = {'fp_v1', 'lexicon'}
        for (m,) in methods:
            assert m in valid, f"Invalid entries uid_method: {m}"


# --- Auto-Discovery (manifest-less DB) ---

class TestAutoDiscovery:
    """Test auto-generated manifest for databases without ui_manifest."""

    def test_manifest_auto_generated(self, no_manifest_client):
        """GET /api/manifest should return auto-generated manifest when no ui_manifest exists."""
        resp = no_manifest_client.get('/api/manifest')
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == 'auto-generated'
        assert 'manifest' in data
        manifest = data['manifest']
        assert 'views' in manifest
        assert 'default_view' in manifest

    def test_auto_manifest_contains_data_tables(self, no_manifest_client):
        """Auto-generated manifest should include species and localities tables."""
        resp = no_manifest_client.get('/api/manifest')
        data = resp.json()
        views = data['manifest']['views']
        assert 'species_table' in views
        assert 'localities_table' in views

    def test_auto_manifest_excludes_meta_tables(self, no_manifest_client):
        """Auto-generated manifest should not include SCODA metadata tables."""
        resp = no_manifest_client.get('/api/manifest')
        data = resp.json()
        views = data['manifest']['views']
        # No SCODA meta table should appear as a view
        for meta_table in ('artifact_metadata', 'provenance', 'schema_descriptions',
                           'ui_display_intent', 'ui_queries', 'ui_manifest'):
            assert f'{meta_table}_table' not in views

    def test_auto_manifest_table_view_structure(self, no_manifest_client):
        """Auto-generated table view should have correct structure."""
        resp = no_manifest_client.get('/api/manifest')
        view = resp.json()['manifest']['views']['species_table']
        assert view['type'] == 'table'
        assert view['title'] == 'Species'
        assert view['source_query'] == 'auto__species_list'
        assert len(view['columns']) == 5  # id, name, genus, habitat, is_extinct
        assert view['searchable'] is True
        assert 'on_row_click' in view  # species has PK

    def test_auto_manifest_detail_view_created(self, no_manifest_client):
        """Auto-generated detail view should exist for tables with PK."""
        resp = no_manifest_client.get('/api/manifest')
        views = resp.json()['manifest']['views']
        assert 'species_detail' in views
        detail = views['species_detail']
        assert detail['type'] == 'detail'
        assert '/api/auto/detail/species' in detail['source']

    def test_auto_query_execute(self, no_manifest_client):
        """auto__{table}_list queries should return data."""
        resp = no_manifest_client.get('/api/queries/auto__species_list/execute')
        assert resp.status_code == 200
        data = resp.json()
        assert data['query'] == 'auto__species_list'
        assert data['row_count'] == 3
        assert len(data['rows']) == 3
        names = [r['name'] for r in data['rows']]
        assert 'Paradoxides davidis' in names

    def test_auto_query_nonexistent_table(self, no_manifest_client):
        """auto__ query for non-existent table should return 404."""
        resp = no_manifest_client.get('/api/queries/auto__nonexistent_list/execute')
        assert resp.status_code == 404

    def test_auto_detail_endpoint(self, no_manifest_client):
        """GET /api/auto/detail/{table}?id=N should return single row."""
        resp = no_manifest_client.get('/api/auto/detail/species?id=1')
        assert resp.status_code == 200
        data = resp.json()
        assert data['name'] == 'Paradoxides davidis'
        assert data['genus'] == 'Paradoxides'

    def test_auto_detail_not_found(self, no_manifest_client):
        """Auto detail with invalid id should return 404."""
        resp = no_manifest_client.get('/api/auto/detail/species?id=999')
        assert resp.status_code == 404

    def test_auto_detail_missing_id(self, no_manifest_client):
        """Auto detail without id param should return 400."""
        resp = no_manifest_client.get('/api/auto/detail/species')
        assert resp.status_code == 400

    def test_auto_detail_nonexistent_table(self, no_manifest_client):
        """Auto detail for non-existent table should return 404."""
        resp = no_manifest_client.get('/api/auto/detail/nonexistent?id=1')
        assert resp.status_code == 404

    def test_existing_manifest_unchanged(self, generic_client):
        """Databases WITH ui_manifest should still use the stored manifest."""
        resp = generic_client.get('/api/manifest')
        assert resp.status_code == 200
        data = resp.json()
        # Should be the test fixture manifest, not auto-generated
        assert data['name'] == 'default'
        assert 'category_tree' in data['manifest']['views']

    def test_auto_manifest_default_view(self, no_manifest_client):
        """Default view should be the first table alphabetically."""
        resp = no_manifest_client.get('/api/manifest')
        data = resp.json()
        # 'localities' < 'species' alphabetically
        assert data['manifest']['default_view'] == 'localities_table'

    def test_auto_query_localities(self, no_manifest_client):
        """auto__localities_list should return locality data."""
        resp = no_manifest_client.get('/api/queries/auto__localities_list/execute')
        assert resp.status_code == 200
        data = resp.json()
        assert data['row_count'] == 2
        names = [r['name'] for r in data['rows']]
        assert 'Burgess Shale' in names

    def test_auto_detail_blocks_metadata_table(self, generic_client):
        """Auto detail endpoint should block access to SCODA metadata tables."""
        for meta_table in ('artifact_metadata', 'provenance', 'schema_descriptions',
                           'ui_display_intent', 'ui_queries', 'ui_manifest'):
            resp = generic_client.get(f'/api/auto/detail/{meta_table}?id=1')
            assert resp.status_code == 403, f"{meta_table} should return 403"

    def test_auto_detail_blocks_metadata_no_manifest(self, no_manifest_client):
        """Auto detail metadata blocking works even without manifest."""
        resp = no_manifest_client.get('/api/auto/detail/ui_queries?id=1')
        assert resp.status_code == 403


# --- Manifest Validator ---

def _make_validator_db(tmp_path, manifest, queries=None):
    """Helper: create a minimal DB with ui_manifest + ui_queries for validation tests."""
    db_path = str(tmp_path / "validate_test.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""CREATE TABLE ui_manifest (
        name TEXT PRIMARY KEY, description TEXT, manifest_json TEXT NOT NULL, created_at TEXT NOT NULL)""")
    c.execute("""CREATE TABLE ui_queries (
        id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT,
        sql TEXT NOT NULL, params_json TEXT, created_at TEXT NOT NULL)""")
    c.execute("INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
              ('default', 'test', json.dumps(manifest), '2026-01-01'))
    if queries:
        for i, qname in enumerate(queries, 1):
            c.execute("INSERT INTO ui_queries (id, name, sql, created_at) VALUES (?, ?, ?, ?)",
                      (i, qname, 'SELECT 1', '2026-01-01'))
    conn.commit()
    conn.close()
    return db_path


class TestManifestValidator:
    """Tests for scripts/validate_manifest.py"""

    def test_valid_manifest_no_errors(self, tmp_path):
        """A well-formed manifest should produce 0 errors."""
        manifest = {
            "default_view": "my_table",
            "views": {
                "my_table": {
                    "type": "table",
                    "source_query": "items_list",
                    "columns": [{"key": "name", "label": "Name"}],
                    "default_sort": {"key": "name", "direction": "asc"},
                    "on_row_click": {"detail_view": "my_detail", "id_key": "id"}
                },
                "my_detail": {
                    "type": "detail",
                    "source_query": "item_detail",
                    "source_param": "item_id",
                    "sub_queries": {},
                    "sections": [
                        {"title": "Info", "type": "field_grid", "fields": [{"key": "name"}]}
                    ]
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest,
                                     queries=['items_list', 'item_detail'])
        errors, warnings = validate_db(db_path)
        assert errors == []

    def test_default_view_missing(self, tmp_path):
        """default_view referencing non-existent view should be ERROR."""
        manifest = {
            "default_view": "nonexistent",
            "views": {
                "real_view": {"type": "table", "source_query": "q1",
                              "columns": [], "default_sort": {"key": "x"}}
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("default_view" in e and "nonexistent" in e for e in errors)

    def test_source_query_missing(self, tmp_path):
        """source_query referencing non-existent query should be ERROR."""
        manifest = {
            "default_view": "t",
            "views": {
                "t": {"type": "table", "source_query": "deleted_query",
                       "columns": [], "default_sort": {"key": "x"}}
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=[])
        errors, warnings = validate_db(db_path)
        assert any("source_query" in e and "deleted_query" in e for e in errors)

    def test_on_row_click_detail_view_missing(self, tmp_path):
        """on_row_click.detail_view referencing non-existent view should be ERROR."""
        manifest = {
            "default_view": "t",
            "views": {
                "t": {
                    "type": "table", "source_query": "q1",
                    "columns": [{"key": "name"}],
                    "default_sort": {"key": "name"},
                    "on_row_click": {"detail_view": "ghost_detail", "id_key": "id"}
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("on_row_click" in e and "ghost_detail" in e for e in errors)

    def test_default_sort_key_not_in_columns(self, tmp_path):
        """default_sort.key not in columns should be ERROR."""
        manifest = {
            "default_view": "t",
            "views": {
                "t": {
                    "type": "table", "source_query": "q1",
                    "columns": [{"key": "name", "label": "Name"}],
                    "default_sort": {"key": "nonexistent_col", "direction": "asc"},
                    "on_row_click": {"detail_view": "d", "id_key": "id"}
                },
                "d": {"type": "detail", "source_query": "q2", "sections": []}
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1', 'q2'])
        errors, warnings = validate_db(db_path)
        assert any("default_sort.key" in e and "nonexistent_col" in e for e in errors)

    def test_view_type_missing(self, tmp_path):
        """View without 'type' should be ERROR."""
        manifest = {
            "default_view": "t",
            "views": {"t": {"source_query": "q1"}}
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("missing 'type'" in e for e in errors)

    def test_chart_options_missing_required_keys(self, tmp_path):
        """chart_options missing required keys should be ERROR."""
        manifest = {
            "default_view": "c",
            "views": {
                "c": {
                    "type": "chart", "source_query": "q1",
                    "chart_options": {"id_key": "id"}  # missing many required keys
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("chart_options" in e and "missing required keys" in e for e in errors)

    def test_tree_item_query_missing(self, tmp_path):
        """tree_options.item_query referencing non-existent query should be ERROR."""
        manifest = {
            "default_view": "tree",
            "views": {
                "tree": {
                    "type": "tree", "source_query": "q1",
                    "tree_options": {
                        "id_key": "id", "parent_key": "pid", "label_key": "name",
                        "item_query": "deleted_query"
                    }
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("item_query" in e and "deleted_query" in e for e in errors)

    def test_linked_table_missing_data_key(self, tmp_path):
        """linked_table section without data_key should be ERROR."""
        manifest = {
            "default_view": "d",
            "views": {
                "d": {
                    "type": "detail", "source_query": "q1",
                    "sections": [
                        {"title": "Items", "type": "linked_table",
                         "columns": [{"key": "name"}]}
                        # missing data_key
                    ]
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("linked_table" in e and "data_key" in e for e in errors)

    def test_field_grid_missing_fields(self, tmp_path):
        """field_grid section without 'fields' should be ERROR."""
        manifest = {
            "default_view": "d",
            "views": {
                "d": {
                    "type": "detail", "source_query": "q1",
                    "sections": [
                        {"title": "Info", "type": "field_grid"}
                        # missing fields
                    ]
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("field_grid" in e and "fields" in e for e in errors)

    def test_sub_queries_query_missing(self, tmp_path):
        """sub_queries referencing non-existent query should be ERROR."""
        manifest = {
            "default_view": "d",
            "views": {
                "d": {
                    "type": "detail", "source_query": "q1",
                    "sub_queries": {
                        "items": {"query": "ghost_query", "params": {"id": "id"}}
                    },
                    "sections": []
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert any("sub_queries" in e and "ghost_query" in e for e in errors)

    def test_no_on_row_click_is_warning(self, tmp_path):
        """Table without on_row_click should produce WARNING, not ERROR."""
        manifest = {
            "default_view": "t",
            "views": {
                "t": {
                    "type": "table", "source_query": "q1",
                    "columns": [{"key": "name"}],
                    "default_sort": {"key": "name"}
                }
            }
        }
        db_path = _make_validator_db(tmp_path, manifest, queries=['q1'])
        errors, warnings = validate_db(db_path)
        assert errors == []
        assert any("on_row_click" in w for w in warnings)

    def test_no_ui_manifest_table(self, tmp_path):
        """DB without ui_manifest table should return an error."""
        db_path = str(tmp_path / "no_manifest.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE foo (id INTEGER)")
        conn.close()
        errors, warnings = validate_db(db_path)
        assert len(errors) == 1
        assert "ui_manifest" in errors[0]

    def test_real_test_db_fixture(self, generic_db):
        """The generic_db fixture manifest should have 0 errors."""
        canonical_db_path, _ = generic_db
        errors, warnings = validate_db(canonical_db_path)
        assert errors == [], f"Unexpected errors: {errors}"


# ---------------------------------------------------------------------------
# S-5: SemVer parsing and version constraint checking
# ---------------------------------------------------------------------------

class TestSemVer:
    """Tests for _parse_semver and _check_version_constraint."""

    def test_parse_full_version(self):
        from scoda_engine_core import _parse_semver
        assert _parse_semver("1.2.3") == (1, 2, 3)

    def test_parse_two_part(self):
        from scoda_engine_core import _parse_semver
        assert _parse_semver("1.2") == (1, 2, 0)

    def test_parse_one_part(self):
        from scoda_engine_core import _parse_semver
        assert _parse_semver("3") == (3, 0, 0)

    def test_parse_with_prerelease(self):
        from scoda_engine_core import _parse_semver
        assert _parse_semver("1.2.3-alpha") == (1, 2, 3)

    def test_parse_invalid_raises(self):
        from scoda_engine_core import _parse_semver
        with pytest.raises(ValueError):
            _parse_semver("abc")

    def test_parse_empty_raises(self):
        from scoda_engine_core import _parse_semver
        with pytest.raises(ValueError):
            _parse_semver("")

    def test_parse_none_raises(self):
        from scoda_engine_core import _parse_semver
        with pytest.raises(ValueError):
            _parse_semver(None)

    def test_constraint_exact_match(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("1.0.0", "==1.0.0") is True
        assert _check_version_constraint("1.0.1", "==1.0.0") is False

    def test_constraint_plain_version(self):
        """Plain version string should be treated as ==."""
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("0.3.0", "0.3.0") is True
        assert _check_version_constraint("0.3.1", "0.3.0") is False

    def test_constraint_range(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("0.1.5", ">=0.1.1,<0.2.0") is True
        assert _check_version_constraint("0.2.0", ">=0.1.1,<0.2.0") is False
        assert _check_version_constraint("0.1.0", ">=0.1.1,<0.2.0") is False

    def test_constraint_empty(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("1.0.0", "") is True
        assert _check_version_constraint("1.0.0", None) is True

    def test_constraint_not_equal(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("1.0.0", "!=1.0.0") is False
        assert _check_version_constraint("1.0.1", "!=1.0.0") is True

    def test_constraint_gt_lt(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("2.0.0", ">1.0.0") is True
        assert _check_version_constraint("1.0.0", ">1.0.0") is False
        assert _check_version_constraint("0.9.0", "<1.0.0") is True
        assert _check_version_constraint("1.0.0", "<1.0.0") is False

    def test_constraint_lte(self):
        from scoda_engine_core import _check_version_constraint
        assert _check_version_constraint("1.0.0", "<=1.0.0") is True
        assert _check_version_constraint("1.0.1", "<=1.0.0") is False


# ---------------------------------------------------------------------------
# S-5: Checksum verification on load
# ---------------------------------------------------------------------------

class TestChecksumOnLoad:
    """Tests for automatic checksum verification during ScodaPackage.__init__."""

    def test_normal_load_passes(self, generic_db, tmp_path):
        """A valid .scoda package should load without error."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "good.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.verify_checksum() is True

    def test_corrupted_raises_checksum_error(self, generic_db, tmp_path):
        """A .scoda with tampered data.db should raise ScodaChecksumError."""
        from scoda_engine_core import ScodaPackage, ScodaChecksumError
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "bad.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        # Tamper: rewrite data.db inside the ZIP with garbage
        tampered_path = str(tmp_path / "tampered.scoda")
        with zipfile.ZipFile(scoda_path, 'r') as zf_in:
            manifest = json.loads(zf_in.read('manifest.json'))
            with zipfile.ZipFile(tampered_path, 'w') as zf_out:
                zf_out.writestr('manifest.json', json.dumps(manifest))
                zf_out.writestr('data.db', b'corrupted data here')
                zf_out.writestr('assets/', '')

        with pytest.raises(ScodaChecksumError):
            ScodaPackage(tampered_path)

    def test_verify_checksum_false_skips(self, generic_db, tmp_path):
        """verify_checksum=False should skip checksum check."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "skip.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        # Tamper
        tampered_path = str(tmp_path / "tampered2.scoda")
        with zipfile.ZipFile(scoda_path, 'r') as zf_in:
            manifest = json.loads(zf_in.read('manifest.json'))
            with zipfile.ZipFile(tampered_path, 'w') as zf_out:
                zf_out.writestr('manifest.json', json.dumps(manifest))
                zf_out.writestr('data.db', b'corrupted data here')
                zf_out.writestr('assets/', '')

        # Should NOT raise
        with ScodaPackage(tampered_path, verify_checksum=False) as pkg:
            assert pkg.name == manifest['name']

    def test_no_checksum_in_manifest_passes(self, generic_db, tmp_path):
        """Package without data_checksum_sha256 should load fine (backward compat)."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db
        scoda_path = str(tmp_path / "nochecksum.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        # Remove checksum from manifest
        no_cs_path = str(tmp_path / "nocs.scoda")
        with zipfile.ZipFile(scoda_path, 'r') as zf_in:
            manifest = json.loads(zf_in.read('manifest.json'))
            del manifest['data_checksum_sha256']
            db_data = zf_in.read('data.db')
            with zipfile.ZipFile(no_cs_path, 'w') as zf_out:
                zf_out.writestr('manifest.json', json.dumps(manifest))
                zf_out.writestr('data.db', db_data)
                zf_out.writestr('assets/', '')

        with ScodaPackage(no_cs_path) as pkg:
            assert pkg.verify_checksum() is True  # no checksum → True

    def test_registry_skips_bad_checksum(self, generic_db, tmp_path):
        """PackageRegistry.scan() should skip packages with bad checksums."""
        from scoda_engine_core import ScodaPackage, PackageRegistry
        canonical_db, _ = generic_db

        pkg_dir = tmp_path / "reg_cs"
        pkg_dir.mkdir()

        # Create a good package
        good_path = str(pkg_dir / "good.scoda")
        ScodaPackage.create(canonical_db, good_path)

        # Create a tampered package
        tampered_path = str(pkg_dir / "bad.scoda")
        with zipfile.ZipFile(good_path, 'r') as zf_in:
            manifest = json.loads(zf_in.read('manifest.json'))
            manifest['name'] = 'bad-data'
            with zipfile.ZipFile(tampered_path, 'w') as zf_out:
                zf_out.writestr('manifest.json', json.dumps(manifest))
                zf_out.writestr('data.db', b'corrupted')
                zf_out.writestr('assets/', '')

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        names = [p['name'] for p in reg.list_packages()]
        assert 'sample-data' in names
        assert 'bad-data' not in names
        reg.close_all()


# ---------------------------------------------------------------------------
# S-5: Dependency validation (required + version constraint)
# ---------------------------------------------------------------------------

class TestDependencyValidation:
    """Tests for required/optional dependency and version constraint validation."""

    def test_required_missing_raises(self, generic_db, generic_dep_db, tmp_path):
        """Missing required dependency should raise ScodaDependencyError."""
        from scoda_engine_core import ScodaPackage, PackageRegistry, ScodaDependencyError
        canonical_db, _ = generic_db

        pkg_dir = tmp_path / "dep_req"
        pkg_dir.mkdir()

        # Create main with required dep that doesn't exist in pkg_dir
        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [{"name": "missing-dep", "alias": "md"}]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        with pytest.raises(ScodaDependencyError, match="missing-dep"):
            reg.get_db('main')
        reg.close_all()

    def test_optional_missing_skipped(self, generic_db, tmp_path):
        """Missing optional dependency should be skipped (no error)."""
        from scoda_engine_core import ScodaPackage, PackageRegistry
        canonical_db, _ = generic_db

        pkg_dir = tmp_path / "dep_opt"
        pkg_dir.mkdir()

        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [
                                          {"name": "optional-dep", "alias": "opt",
                                           "required": False}
                                      ]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        # Should not raise
        conn = reg.get_db('main')
        databases = conn.execute("PRAGMA database_list").fetchall()
        db_names = [row['name'] for row in databases]
        assert 'opt' not in db_names  # optional dep not attached
        conn.close()
        reg.close_all()

    def test_version_satisfied(self, generic_db, generic_dep_db, tmp_path):
        """Dependency with satisfied version constraint should be attached."""
        from scoda_engine_core import ScodaPackage, PackageRegistry
        canonical_db, _ = generic_db
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "dep_ver_ok"
        pkg_dir.mkdir()

        # dep-data has version 0.3.0
        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})
        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [
                                          {"name": "dep-data", "alias": "dep",
                                           "version": ">=0.2.0,<1.0.0"}
                                      ]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('main')
        databases = conn.execute("PRAGMA database_list").fetchall()
        db_names = [row['name'] for row in databases]
        assert 'dep' in db_names
        conn.close()
        reg.close_all()

    def test_version_not_satisfied_required(self, generic_db, generic_dep_db, tmp_path):
        """Required dep with unsatisfied version should raise ScodaDependencyError."""
        from scoda_engine_core import ScodaPackage, PackageRegistry, ScodaDependencyError
        canonical_db, _ = generic_db
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "dep_ver_bad"
        pkg_dir.mkdir()

        # dep-data has version 0.3.0
        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})
        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [
                                          {"name": "dep-data", "alias": "dep",
                                           "version": ">=1.0.0"}
                                      ]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        with pytest.raises(ScodaDependencyError, match="dep-data"):
            reg.get_db('main')
        reg.close_all()

    def test_version_not_satisfied_optional(self, generic_db, generic_dep_db, tmp_path):
        """Optional dep with unsatisfied version should be skipped."""
        from scoda_engine_core import ScodaPackage, PackageRegistry
        canonical_db, _ = generic_db
        dep_path = generic_dep_db

        pkg_dir = tmp_path / "dep_ver_opt"
        pkg_dir.mkdir()

        ScodaPackage.create(dep_path, str(pkg_dir / "dep-data.scoda"),
                            metadata={"name": "dep-data"})
        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [
                                          {"name": "dep-data", "alias": "dep",
                                           "required": False,
                                           "version": ">=1.0.0"}
                                      ]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        conn = reg.get_db('main')
        databases = conn.execute("PRAGMA database_list").fetchall()
        db_names = [row['name'] for row in databases]
        assert 'dep' not in db_names  # version mismatch, optional → skipped
        conn.close()
        reg.close_all()

    def test_required_default_true(self, generic_db, tmp_path):
        """Dependency without 'required' field should default to required=True."""
        from scoda_engine_core import ScodaPackage, PackageRegistry, ScodaDependencyError
        canonical_db, _ = generic_db

        pkg_dir = tmp_path / "dep_default"
        pkg_dir.mkdir()

        # No 'required' field in dep spec → should default to True
        ScodaPackage.create(canonical_db, str(pkg_dir / "main.scoda"),
                            metadata={"name": "main",
                                      "dependencies": [
                                          {"name": "nonexistent", "alias": "ne"}
                                      ]})

        reg = PackageRegistry()
        reg.scan(str(pkg_dir))

        with pytest.raises(ScodaDependencyError):
            reg.get_db('main')
        reg.close_all()


# ---------------------------------------------------------------------------
# S-5: CHANGELOG.md support
# ---------------------------------------------------------------------------

class TestChangelog:
    """Tests for CHANGELOG.md in .scoda packages."""

    def test_create_with_changelog(self, generic_db, tmp_path):
        """create() with changelog_path should include CHANGELOG.md in ZIP."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db

        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n\n## 1.0.0\n- Initial release\n")

        scoda_path = str(tmp_path / "with_cl.scoda")
        ScodaPackage.create(canonical_db, scoda_path, changelog_path=str(changelog))

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            assert 'CHANGELOG.md' in zf.namelist()

    def test_changelog_property(self, generic_db, tmp_path):
        """changelog property should return the file contents."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db

        cl_text = "# Changelog\n\n## 1.0.0\n- Initial release\n"
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(cl_text, newline="\n")

        scoda_path = str(tmp_path / "cl.scoda")
        ScodaPackage.create(canonical_db, scoda_path, changelog_path=str(changelog))

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.changelog == cl_text

    def test_changelog_none_when_absent(self, generic_db, tmp_path):
        """changelog property should return None when no CHANGELOG.md."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db

        scoda_path = str(tmp_path / "no_cl.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with ScodaPackage(scoda_path) as pkg:
            assert pkg.changelog is None

    def test_create_without_changelog_path(self, generic_db, tmp_path):
        """create() without changelog_path should work fine (backward compat)."""
        from scoda_engine_core import ScodaPackage
        canonical_db, _ = generic_db

        scoda_path = str(tmp_path / "no_cl2.scoda")
        ScodaPackage.create(canonical_db, scoda_path)

        with zipfile.ZipFile(scoda_path, 'r') as zf:
            assert 'CHANGELOG.md' not in zf.namelist()
