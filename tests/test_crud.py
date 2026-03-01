"""
Tests for the CRUD framework (entity_schema, crud_engine, REST endpoints).

Uses generic fixtures (items/categories tables) — no domain-specific data.
"""

import pytest


# ═══════════════════════════════════════════════════════════════════════
# Entity types endpoint
# ═══════════════════════════════════════════════════════════════════════

def test_list_entity_types(crud_client):
    """GET /api/entities returns entity schemas."""
    resp = crud_client.get('/api/entities')
    assert resp.status_code == 200
    data = resp.json()
    assert 'item' in data
    assert 'category' in data
    assert data['item']['table'] == 'items'
    assert data['item']['pk'] == 'id'
    assert 'name' in data['item']['fields']


def test_no_editable_entities(generic_client):
    """GET /api/entities returns 404 when no editable_entities in manifest."""
    resp = generic_client.get('/api/entities')
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# CRUD operations
# ═══════════════════════════════════════════════════════════════════════

def test_create_entity(crud_client):
    """POST /api/entities/item creates a new item."""
    resp = crud_client.post('/api/entities/item', json={
        'name': 'Thermodynamics',
        'author': 'Carnot',
        'year': '1824',
        'status': 'active',
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data['name'] == 'Thermodynamics'
    assert data['author'] == 'Carnot'
    assert data['id'] is not None


def test_read_entity(crud_client):
    """GET /api/entities/item/1 returns a single item."""
    resp = crud_client.get('/api/entities/item/1')
    assert resp.status_code == 200
    data = resp.json()
    assert data['name'] == 'Gravity'
    assert data['id'] == 1


def test_read_entity_not_found(crud_client):
    """GET /api/entities/item/999 returns 404."""
    resp = crud_client.get('/api/entities/item/999')
    assert resp.status_code == 404


def test_update_entity(crud_client):
    """PATCH /api/entities/item/1 updates fields."""
    resp = crud_client.patch('/api/entities/item/1', json={
        'author': 'Isaac Newton',
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data['author'] == 'Isaac Newton'
    assert data['name'] == 'Gravity'  # unchanged


def test_update_entity_not_found(crud_client):
    """PATCH /api/entities/item/999 returns 404."""
    resp = crud_client.patch('/api/entities/item/999', json={'name': 'X'})
    assert resp.status_code == 404


def test_delete_entity(crud_client):
    """DELETE /api/entities/item/3 deletes an item."""
    resp = crud_client.delete('/api/entities/item/3')
    assert resp.status_code == 200
    # Verify deleted
    resp2 = crud_client.get('/api/entities/item/3')
    assert resp2.status_code == 404


def test_delete_entity_not_found(crud_client):
    """DELETE /api/entities/item/999 returns 404."""
    resp = crud_client.delete('/api/entities/item/999')
    assert resp.status_code == 404


def test_delete_not_allowed(crud_client):
    """DELETE /api/entities/category/1 returns 403 — delete not in operations."""
    resp = crud_client.delete('/api/entities/category/1')
    assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════
# List + pagination + search
# ═══════════════════════════════════════════════════════════════════════

def test_list_entities(crud_client):
    """GET /api/entities/item returns a paginated list."""
    resp = crud_client.get('/api/entities/item')
    assert resp.status_code == 200
    data = resp.json()
    assert 'rows' in data
    assert 'total' in data
    assert data['total'] == 3
    assert len(data['rows']) == 3


def test_list_with_pagination(crud_client):
    """GET /api/entities/item?page=1&per_page=2 paginates."""
    resp = crud_client.get('/api/entities/item?page=1&per_page=2')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data['rows']) == 2
    assert data['total'] == 3
    assert data['pages'] == 2


def test_list_with_search(crud_client):
    """GET /api/entities/item?search=grav finds matching items."""
    resp = crud_client.get('/api/entities/item?search=grav')
    assert resp.status_code == 200
    data = resp.json()
    assert data['total'] == 1
    assert data['rows'][0]['name'] == 'Gravity'


# ═══════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════

def test_required_field_missing(crud_client):
    """POST without required field returns 400."""
    resp = crud_client.post('/api/entities/item', json={
        'author': 'Someone',
    })
    assert resp.status_code == 400
    assert 'name' in resp.json()['error'].lower()


def test_enum_validation(crud_client):
    """POST with invalid enum value returns 400."""
    resp = crud_client.post('/api/entities/item', json={
        'name': 'Test',
        'status': 'INVALID_STATUS',
    })
    assert resp.status_code == 400
    assert 'status' in resp.json()['error'].lower()


def test_fk_validation(crud_client):
    """POST with non-existent FK returns 400."""
    resp = crud_client.post('/api/entities/item', json={
        'name': 'Test FK',
        'category_id': 999,
    })
    assert resp.status_code == 400
    assert 'FK' in resp.json()['error'] or 'fk' in resp.json()['error'].lower()


def test_unique_constraint(crud_client):
    """POST duplicate name returns 409."""
    resp = crud_client.post('/api/entities/item', json={
        'name': 'Gravity',  # already exists
    })
    assert resp.status_code == 409
    assert 'Duplicate' in resp.json()['error']


def test_unknown_field_rejected(crud_client):
    """POST with unknown field returns 400."""
    resp = crud_client.post('/api/entities/item', json={
        'name': 'Test',
        'nonexistent_field': 'value',
    })
    assert resp.status_code == 400
    assert 'Unknown' in resp.json()['error']


# ═══════════════════════════════════════════════════════════════════════
# Auth guard
# ═══════════════════════════════════════════════════════════════════════

def test_viewer_mode_blocks_write(crud_viewer_client):
    """POST in viewer mode returns 403."""
    resp = crud_viewer_client.post('/api/entities/item', json={
        'name': 'Should Fail',
    })
    assert resp.status_code == 403


def test_viewer_mode_allows_read(crud_viewer_client):
    """GET in viewer mode works fine."""
    resp = crud_viewer_client.get('/api/entities/item/1')
    assert resp.status_code == 200


def test_viewer_mode_blocks_patch(crud_viewer_client):
    """PATCH in viewer mode returns 403."""
    resp = crud_viewer_client.patch('/api/entities/item/1', json={'name': 'X'})
    assert resp.status_code == 403


def test_viewer_mode_blocks_delete(crud_viewer_client):
    """DELETE in viewer mode returns 403."""
    resp = crud_viewer_client.delete('/api/entities/item/1')
    assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════
# Search endpoint
# ═══════════════════════════════════════════════════════════════════════

def test_search_endpoint(crud_client):
    """GET /api/search/item?q=grav returns matching items."""
    resp = crud_client.get('/api/search/item?q=grav')
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    names = [r.get('name', '') for r in results]
    assert any('Gravity' in n for n in names)


def test_search_endpoint_unknown_type(crud_client):
    """GET /api/search/nonexistent returns 404."""
    resp = crud_client.get('/api/search/nonexistent?q=test')
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# Entity type not found
# ═══════════════════════════════════════════════════════════════════════

def test_crud_unknown_entity_type(crud_client):
    """CRUD on unknown entity type returns 404."""
    assert crud_client.get('/api/entities/nonexistent').status_code == 404
    assert crud_client.get('/api/entities/nonexistent/1').status_code == 404
    assert crud_client.post('/api/entities/nonexistent', json={'name': 'x'}).status_code == 404
    assert crud_client.patch('/api/entities/nonexistent/1', json={'name': 'x'}).status_code == 404
    assert crud_client.delete('/api/entities/nonexistent/1').status_code == 404


# ═══════════════════════════════════════════════════════════════════════
# Manifest mode field
# ═══════════════════════════════════════════════════════════════════════

def test_manifest_includes_mode(crud_client):
    """GET /api/manifest includes mode field."""
    resp = crud_client.get('/api/manifest')
    assert resp.status_code == 200
    assert resp.json()['mode'] == 'admin'


def test_manifest_viewer_mode(crud_viewer_client):
    """GET /api/manifest in viewer mode returns mode=viewer."""
    resp = crud_viewer_client.get('/api/manifest')
    assert resp.status_code == 200
    assert resp.json()['mode'] == 'viewer'
