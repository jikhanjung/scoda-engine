"""
SCODA Desktop Web Interface
FastAPI application for browsing SCODA data packages

Multi-package serving: all per-package endpoints live under
``/api/{package}/...``; global endpoints (packages list, health check)
remain at the app level.
"""

from fastapi import FastAPI, Request, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Optional
import json
import logging
import os
import sqlite3
import time

logger = logging.getLogger(__name__)

from scoda_engine_core import get_registry
from scoda_engine import __version__ as ENGINE_VERSION

ENGINE_NAME = os.environ.get('SCODA_ENGINE_NAME', 'SCODA Desktop')

app = FastAPI(title=ENGINE_NAME)

# Admin/Viewer mode — set via SCODA_MODE env var or _set_scoda_mode()
SCODA_MODE = os.environ.get('SCODA_MODE', 'viewer')


def _set_scoda_mode(mode: str):
    """Set the server mode (for testing)."""
    global SCODA_MODE
    SCODA_MODE = mode


def _require_admin():
    """Raise 403 if not in admin mode."""
    if SCODA_MODE != 'admin':
        raise HTTPException(status_code=403, detail="Admin mode required")

# Tables that are SCODA metadata — excluded from auto-discovery
SCODA_META_TABLES = {'artifact_metadata', 'provenance', 'schema_descriptions',
                     'ui_display_intent', 'ui_queries', 'ui_manifest'}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class ProvenanceItem(BaseModel):
    id: int
    source_type: str
    citation: str
    description: Optional[str] = None
    year: Optional[int] = None
    url: Optional[str] = None

class DisplayIntentItem(BaseModel):
    id: int
    entity: str
    default_view: str
    description: Optional[str] = None
    source_query: Optional[str] = None
    priority: int = 0

class QueryItem(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    params: Optional[str] = None
    created_at: str

class QueryResult(BaseModel):
    query: str
    columns: list[str]
    row_count: int
    rows: list[dict[str, Any]]

class PackageInfo(BaseModel):
    name: str = ""
    artifact_id: str = ""
    version: str = ""
    description: str = ""

class ManifestResponse(BaseModel):
    name: str
    description: Optional[str] = None
    manifest: dict[str, Any]
    created_at: str
    package: PackageInfo
    engine_version: str = ""
    engine_name: str = "SCODA Desktop"
    mode: str = "viewer"

class AnnotationItem(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    entity_name: Optional[str] = None
    annotation_type: str
    content: str
    author: Optional[str] = None
    created_at: str

class ErrorResponse(BaseModel):
    error: str

class DeleteResponse(BaseModel):
    message: str
    id: int


# ---------------------------------------------------------------------------
# Core helper functions (conn-based, shared by all routes)
# ---------------------------------------------------------------------------

def _auto_generate_manifest(conn):
    """Generate a manifest automatically from DB schema when ui_manifest is absent."""
    cursor = conn.cursor()

    # 1. User data tables (exclude SCODA metadata tables)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()
              if r[0] not in SCODA_META_TABLES and not r[0].startswith('sqlite_')]
    tables.sort()

    if not tables:
        return None

    # 2. Build views for each table
    views = {}
    for table in tables:
        cols_info = cursor.execute(f"PRAGMA table_info([{table}])").fetchall()
        # cols_info row: (cid, name, type, notnull, default, pk)
        pk_col = None
        columns = []
        for c in cols_info:
            col_name, col_type, is_pk = c[1], c[2], c[5]
            if is_pk:
                pk_col = col_name
            columns.append({
                "key": col_name,
                "label": col_name.replace('_', ' ').title(),
                "sortable": True,
                "searchable": col_type.upper() in ('TEXT', '')
            })

        # 3. Table view
        title = table.replace('_', ' ').title()
        table_view_key = f"{table}_table"
        view_def = {
            "type": "table",
            "title": title,
            "source_query": f"auto__{table}_list",
            "columns": columns,
            "default_sort": {"key": columns[0]["key"], "direction": "asc"},
            "searchable": True
        }
        if pk_col:
            view_def["on_row_click"] = {
                "detail_view": f"{table}_detail",
                "id_key": pk_col
            }
        views[table_view_key] = view_def

        # 4. Detail view (only for tables with a PK)
        if pk_col:
            views[f"{table}_detail"] = {
                "type": "detail",
                "title": f"{title} Detail",
                "source": f"/api/auto/detail/{table}?id={{id}}",
                "sections": [{
                    "type": "field_grid",
                    "fields": [{"key": c["key"], "label": c["label"]} for c in columns]
                }]
            }

    first_view = f"{tables[0]}_table"
    logger.info("Auto-generated manifest for %d tables", len(tables))
    return {
        "default_view": first_view,
        "views": views
    }


def _fetch_manifest(conn):
    """Fetch UI manifest from a DB connection.

    Falls back to auto-generating a manifest from DB schema if ui_manifest
    table is missing or has no 'default' row.
    """
    cursor = conn.cursor()

    # Check if ui_manifest table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ui_manifest'")
    if cursor.fetchone():
        cursor.execute("""
            SELECT name, description, manifest_json, created_at
            FROM ui_manifest
            WHERE name = 'default'
        """)
        row = cursor.fetchone()
        if row:
            # Include package info from artifact_metadata
            cursor.execute("SELECT key, value FROM artifact_metadata")
            meta = {r['key']: r['value'] for r in cursor.fetchall()}

            return {
                'name': row['name'],
                'description': row['description'],
                'manifest': json.loads(row['manifest_json']),
                'created_at': row['created_at'],
                'package': {
                    'name': meta.get('name', ''),
                    'artifact_id': meta.get('artifact_id', ''),
                    'version': meta.get('version', ''),
                    'description': meta.get('description', ''),
                },
                'engine_version': ENGINE_VERSION,
                'engine_name': ENGINE_NAME,
            }

    # Fallback: auto-generate manifest from DB schema
    manifest = _auto_generate_manifest(conn)
    if not manifest or not manifest['views']:
        return None

    # Package info from artifact_metadata (if table exists)
    meta = {}
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='artifact_metadata'")
    if cursor.fetchone():
        cursor.execute("SELECT key, value FROM artifact_metadata")
        meta = {r['key']: r['value'] for r in cursor.fetchall()}

    return {
        'name': 'auto-generated',
        'description': 'Auto-generated from database schema',
        'manifest': manifest,
        'created_at': '',
        'package': {
            'name': meta.get('name', ''),
            'artifact_id': meta.get('artifact_id', ''),
            'version': meta.get('version', ''),
            'description': meta.get('description', ''),
        },
        'engine_version': ENGINE_VERSION,
    }


def _fetch_metadata(conn):
    """Fetch artifact metadata from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM artifact_metadata")
    return {row['key']: row['value'] for row in cursor.fetchall()}


def _fetch_provenance(conn):
    """Fetch provenance from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, source_type, citation, description, year, url
        FROM provenance ORDER BY id
    """)
    return [{
        'id': s['id'],
        'source_type': s['source_type'],
        'citation': s['citation'],
        'description': s['description'],
        'year': s['year'],
        'url': s['url']
    } for s in cursor.fetchall()]


def _fetch_display_intent(conn):
    """Fetch display intent from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, entity, default_view, description, source_query, priority
        FROM ui_display_intent ORDER BY entity, priority
    """)
    return [{
        'id': i['id'],
        'entity': i['entity'],
        'default_view': i['default_view'],
        'description': i['description'],
        'source_query': i['source_query'],
        'priority': i['priority']
    } for i in cursor.fetchall()]


def _fetch_queries(conn):
    """Fetch named queries list from a DB connection."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, description, params_json, created_at
        FROM ui_queries ORDER BY name
    """)
    return [{
        'id': q['id'],
        'name': q['name'],
        'description': q['description'],
        'params': q['params_json'],
        'created_at': q['created_at']
    } for q in cursor.fetchall()]


def _execute_query(conn, query_name, params):
    """Execute a named query and return result dict or error tuple.

    Auto-generated queries (prefix ``auto__``) are handled directly
    without looking up ``ui_queries``.
    """
    cursor = conn.cursor()

    # Auto-generated query: "auto__{table}_list"
    if query_name.startswith('auto__') and query_name.endswith('_list'):
        table = query_name[6:-5]  # "auto__countries_list" → "countries"
        # Verify table exists (SQL injection prevention)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cursor.fetchone():
            return None
        try:
            cursor.execute(f"SELECT * FROM [{table}]")
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return {
                'query': query_name,
                'columns': columns,
                'row_count': len(rows),
                'rows': [dict(r) for r in rows]
            }
        except Exception as e:
            return {'error': str(e)}

    # Standard named query from ui_queries
    cursor.execute("SELECT sql, params_json FROM ui_queries WHERE name = ?", (query_name,))
    query = cursor.fetchone()
    if not query:
        return None
    try:
        # Fill missing optional params with None so COALESCE(:param, default) works
        if query['params_json']:
            declared = json.loads(query['params_json'])
            for pname in declared:
                if pname not in params:
                    params[pname] = None
        cursor.execute(query['sql'], params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return {
            'query': query_name,
            'columns': columns,
            'row_count': len(rows),
            'rows': [dict(row) for row in rows]
        }
    except Exception as e:
        logger.error("Query '%s' failed: %s", query_name, e)
        return {'error': str(e)}


def _fetch_annotations(conn, entity_type, entity_id):
    """Fetch annotations for an entity."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))
    return [{
        'id': a['id'],
        'entity_type': a['entity_type'],
        'entity_id': a['entity_id'],
        'entity_name': a['entity_name'],
        'annotation_type': a['annotation_type'],
        'content': a['content'],
        'author': a['author'],
        'created_at': a['created_at']
    } for a in cursor.fetchall()]


def _create_annotation(conn, data):
    """Create an annotation. Returns (result_dict, status_code)."""
    entity_type = data.get('entity_type')
    entity_id = data.get('entity_id')
    annotation_type = data.get('annotation_type')
    content = data.get('content')
    author = data.get('author')

    if not content:
        return {'error': 'content is required'}, 400
    if not entity_type:
        return {'error': 'entity_type is required'}, 400
    if not annotation_type:
        return {'error': 'annotation_type is required'}, 400

    entity_name = data.get('entity_name')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO overlay.user_annotations (entity_type, entity_id, entity_name, annotation_type, content, author)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, entity_name, annotation_type, content, author))
    conn.commit()

    annotation_id = cursor.lastrowid
    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations WHERE id = ?
    """, (annotation_id,))
    annotation = cursor.fetchone()

    return {
        'id': annotation['id'],
        'entity_type': annotation['entity_type'],
        'entity_id': annotation['entity_id'],
        'entity_name': annotation['entity_name'],
        'annotation_type': annotation['annotation_type'],
        'content': annotation['content'],
        'author': annotation['author'],
        'created_at': annotation['created_at']
    }, 201


def _delete_annotation(conn, annotation_id):
    """Delete an annotation. Returns (result_dict, status_code)."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        return {'error': 'Annotation not found'}, 404

    cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    return {'message': 'Annotation deleted', 'id': annotation_id}, 200


# ---------------------------------------------------------------------------
# Package DB dependency (for multi-package router)
# ---------------------------------------------------------------------------

async def get_package_db(package: str):
    """FastAPI dependency: get DB connection for a named package.

    Looks up the package in the global PackageRegistry.
    The connection is automatically closed when the request finishes.
    """
    try:
        conn = get_registry().get_db(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Package router — all per-package API endpoints under /api/{package}/...
# ---------------------------------------------------------------------------

pkg_router = APIRouter(prefix="/api/{package}")


@pkg_router.get('/detail/{query_name}',
                responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_generic_detail(query_name: str, request: Request,
                       conn: sqlite3.Connection = Depends(get_package_db)):
    """Execute a named query and return the first row as flat JSON."""
    params = dict(request.query_params)
    result = _execute_query(conn, query_name, params)
    if result is None:
        return JSONResponse({'error': f'Query not found: {query_name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    if result['row_count'] == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result['rows'][0]


@pkg_router.get('/composite/{view_name}',
                responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def api_composite_detail(view_name: str, request: Request,
                         conn: sqlite3.Connection = Depends(get_package_db)):
    """Execute manifest-defined composite detail query."""
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)

    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        return JSONResponse({'error': 'No manifest found'}, status_code=404)

    views = manifest_data['manifest'].get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        logger.warning("Composite detail view not found: %s", view_name)
        return JSONResponse({'error': f'Detail view not found: {view_name}'}, status_code=404)

    # Main query — merge request query_params so optional params (e.g. profile_id) are forwarded
    source_param = view.get('source_param', 'id')
    main_params = dict(request.query_params)
    main_params[source_param] = entity_id
    result = _execute_query(conn, view['source_query'], main_params)
    if result and 'error' in result:
        return JSONResponse(result, status_code=400)
    if result is None or result.get('row_count', 0) == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)

    data = dict(result['rows'][0])

    # Sub-queries — also forward request query_params for optional bindings
    extra_params = dict(request.query_params)
    for key, sub_def in view.get('sub_queries', {}).items():
        params = dict(extra_params)
        for param_name, value_source in sub_def.get('params', {}).items():
            if value_source == 'id':
                params[param_name] = entity_id
            elif value_source.startswith('result.'):
                field = value_source[7:]
                params[param_name] = data.get(field, '')
            else:
                params[param_name] = value_source
        sub_result = _execute_query(conn, sub_def['query'], params)
        data[key] = sub_result['rows'] if sub_result and 'rows' in sub_result else []

    return data


@pkg_router.get('/auto/detail/{table_name}',
                responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def api_auto_detail(table_name: str, request: Request,
                    conn: sqlite3.Connection = Depends(get_package_db)):
    """Auto-generated detail: SELECT * FROM table WHERE pk = :id."""
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)

    cursor = conn.cursor()

    # Block access to SCODA metadata tables
    if table_name in SCODA_META_TABLES:
        return JSONResponse({'error': 'Metadata tables not accessible'}, status_code=403)

    # Verify table exists (SQL injection prevention)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        return JSONResponse({'error': f'Table not found: {table_name}'}, status_code=404)

    # Find PK column
    cols_info = cursor.execute(f"PRAGMA table_info([{table_name}])").fetchall()
    pk_col = next((c[1] for c in cols_info if c[5]), 'id')

    try:
        cursor.execute(f"SELECT * FROM [{table_name}] WHERE [{pk_col}] = ?", (entity_id,))
        row = cursor.fetchone()
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)

    if not row:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return dict(row)


@pkg_router.get('/provenance', response_model=list[ProvenanceItem])
def api_provenance(conn: sqlite3.Connection = Depends(get_package_db)):
    """Get data provenance information"""
    return _fetch_provenance(conn)


@pkg_router.get('/display-intent', response_model=list[DisplayIntentItem])
def api_display_intent(conn: sqlite3.Connection = Depends(get_package_db)):
    """Get display intent hints for SCODA viewers"""
    return _fetch_display_intent(conn)


@pkg_router.get('/queries', response_model=list[QueryItem])
def api_queries(conn: sqlite3.Connection = Depends(get_package_db)):
    """Get list of available named queries"""
    return _fetch_queries(conn)


@pkg_router.get('/manifest', response_model=ManifestResponse,
                responses={404: {"model": ErrorResponse}})
def api_manifest(package: str, conn: sqlite3.Connection = Depends(get_package_db)):
    """Get UI manifest with declarative view definitions"""
    # Meta-package: return meta-specific manifest
    reg = get_registry()
    try:
        info = reg.get_package(package)
    except KeyError:
        return JSONResponse({'error': 'Package not found'}, status_code=404)

    if info.get('kind') == 'meta-package':
        pkg_obj = reg._packages[package]['pkg']
        # Return JSONResponse to bypass ManifestResponse model filtering
        return JSONResponse({
            'name': 'meta-package',
            'description': pkg_obj.manifest.get('description', ''),
            'manifest': {
                'default_view': 'meta_tree',
                'views': {
                    'meta_tree': {
                        'type': 'meta_tree',
                        'title': pkg_obj.title,
                        'source_query': 'meta_composite_tree',
                    }
                },
            },
            'created_at': pkg_obj.manifest.get('created_at', ''),
            'package': {
                'name': pkg_obj.name,
                'artifact_id': pkg_obj.name,
                'version': pkg_obj.version,
                'description': pkg_obj.manifest.get('description', ''),
            },
            'engine_version': ENGINE_VERSION,
            'engine_name': ENGINE_NAME,
            'mode': SCODA_MODE,
            'kind': 'meta-package',
            'meta_tree': pkg_obj.meta_tree,
            'package_bindings': pkg_obj.package_bindings,
        })

    result = _fetch_manifest(conn)
    if result:
        result['mode'] = SCODA_MODE
        return result
    return JSONResponse({'error': 'No manifest found'}, status_code=404)


@pkg_router.get('/queries/{name}/execute', response_model=QueryResult,
                responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_query_execute(name: str, request: Request,
                      conn: sqlite3.Connection = Depends(get_package_db)):
    """Execute a named query with optional parameters"""
    params = dict(request.query_params)
    result = _execute_query(conn, name, params)
    if result is None:
        return JSONResponse({'error': f'Query not found: {name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    return result


@pkg_router.get('/annotations/{entity_type}/{entity_id}', response_model=list[AnnotationItem])
def api_get_annotations(entity_type: str, entity_id: int,
                        conn: sqlite3.Connection = Depends(get_package_db)):
    """Get annotations for a specific entity"""
    return _fetch_annotations(conn, entity_type, entity_id)


class AnnotationCreate(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    annotation_type: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None


@pkg_router.post('/annotations', status_code=201,
                 responses={201: {"model": AnnotationItem}, 400: {"model": ErrorResponse}})
def api_create_annotation(body: AnnotationCreate,
                          conn: sqlite3.Connection = Depends(get_package_db)):
    """Create a new annotation"""
    data = body.model_dump()
    result, status = _create_annotation(conn, data)
    return JSONResponse(result, status_code=status)


@pkg_router.delete('/annotations/{annotation_id}',
                   responses={200: {"model": DeleteResponse}, 404: {"model": ErrorResponse}})
def api_delete_annotation(annotation_id: int,
                          conn: sqlite3.Connection = Depends(get_package_db)):
    """Delete an annotation"""
    result, status = _delete_annotation(conn, annotation_id)
    return JSONResponse(result, status_code=status)


# ---------------------------------------------------------------------------
# Preferences API — persist global control values in overlay DB
# Uses overlay.overlay_metadata with 'pref_' key prefix.
# ---------------------------------------------------------------------------

class PreferenceValue(BaseModel):
    value: Any

@pkg_router.get('/preferences')
def api_preferences_all(conn: sqlite3.Connection = Depends(get_package_db)):
    """Get all user preferences (pref_* keys from overlay_metadata)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT key, value FROM overlay.overlay_metadata WHERE key LIKE 'pref_%'"
    )
    rows = cursor.fetchall()
    # Strip 'pref_' prefix and parse JSON values
    result = {}
    for r in rows:
        k = r['key'][5:]  # remove 'pref_' prefix
        try:
            result[k] = json.loads(r['value'])
        except (json.JSONDecodeError, TypeError):
            result[k] = r['value']
    return result


@pkg_router.get('/preferences/{key}')
def api_preference_get(key: str, conn: sqlite3.Connection = Depends(get_package_db)):
    """Get a single preference value."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM overlay.overlay_metadata WHERE key = ?",
        (f'pref_{key}',)
    )
    row = cursor.fetchone()
    if not row:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    try:
        val = json.loads(row['value'])
    except (json.JSONDecodeError, TypeError):
        val = row['value']
    return {'key': key, 'value': val}


@pkg_router.put('/preferences/{key}')
def api_preference_put(key: str, body: PreferenceValue,
                       conn: sqlite3.Connection = Depends(get_package_db)):
    """Store a preference value."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO overlay.overlay_metadata (key, value) VALUES (?, ?)",
        (f'pref_{key}', json.dumps(body.value))
    )
    conn.commit()
    return {'key': key, 'value': body.value}


# ---------------------------------------------------------------------------
# CRUD Entity endpoints — manifest-driven editable_entities
# ---------------------------------------------------------------------------

from .entity_schema import parse_editable_entities, EntitySchema
from .crud_engine import CrudEngine


def _get_entity_schemas(conn) -> dict[str, EntitySchema]:
    """Load editable_entities from manifest and parse into schemas."""
    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        return {}
    manifest = manifest_data.get('manifest', {})
    return parse_editable_entities(manifest)


@pkg_router.get('/entities')
def api_entity_types(conn: sqlite3.Connection = Depends(get_package_db)):
    """List all editable entity types with their schemas."""
    schemas = _get_entity_schemas(conn)
    if not schemas:
        return JSONResponse({'error': 'No editable entities defined'}, status_code=404)
    result = {}
    for name, schema in schemas.items():
        result[name] = {
            'table': schema.table,
            'pk': schema.pk,
            'operations': sorted(schema.operations),
            'fields': {
                fname: {
                    'type': fdef.type,
                    'required': fdef.required,
                    'enum': fdef.enum,
                    'fk': fdef.fk,
                    'default': fdef.default,
                    'label': fdef.label,
                    'readonly_on_edit': fdef.readonly_on_edit,
                }
                for fname, fdef in schema.fields.items()
            },
        }
    return result


@pkg_router.get('/entities/{entity_type}')
def api_entity_list(entity_type: str, request: Request,
                    conn: sqlite3.Connection = Depends(get_package_db)):
    """List entities with pagination and search."""
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    if 'read' not in schema.operations:
        return JSONResponse({'error': 'Read not allowed'}, status_code=403)

    params = dict(request.query_params)
    page = int(params.pop('page', 1))
    per_page = int(params.pop('per_page', 50))
    search = params.pop('search', None)
    q = params.pop('q', None)
    search = search or q

    engine = CrudEngine(conn, schema)
    return engine.list(filters=params, page=page, per_page=per_page, search=search)


@pkg_router.get('/entities/{entity_type}/{pk}')
def api_entity_read(entity_type: str, pk: str,
                    conn: sqlite3.Connection = Depends(get_package_db)):
    """Get a single entity by primary key."""
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    if 'read' not in schema.operations:
        return JSONResponse({'error': 'Read not allowed'}, status_code=403)

    engine = CrudEngine(conn, schema)
    try:
        pk_val = int(pk)
    except ValueError:
        pk_val = pk
    result = engine.read(pk_val)
    if result is None:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result


@pkg_router.post('/entities/{entity_type}', status_code=201)
async def api_entity_create(entity_type: str, request: Request,
                            conn: sqlite3.Connection = Depends(get_package_db)):
    """Create a new entity."""
    _require_admin()
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    if 'create' not in schema.operations:
        return JSONResponse({'error': 'Create not allowed'}, status_code=403)

    data = await request.json()
    engine = CrudEngine(conn, schema)
    try:
        result = engine.create(data)
    except ValueError as e:
        msg = str(e)
        if 'Duplicate' in msg or 'UNIQUE' in msg:
            return JSONResponse({'error': msg}, status_code=409)
        return JSONResponse({'error': msg}, status_code=400)
    return JSONResponse(result, status_code=201)


@pkg_router.patch('/entities/{entity_type}/{pk}')
async def api_entity_update(entity_type: str, pk: str, request: Request,
                            conn: sqlite3.Connection = Depends(get_package_db)):
    """Partially update an entity."""
    _require_admin()
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    if 'update' not in schema.operations:
        return JSONResponse({'error': 'Update not allowed'}, status_code=403)

    data = await request.json()
    try:
        pk_val = int(pk)
    except ValueError:
        pk_val = pk
    engine = CrudEngine(conn, schema)
    try:
        result = engine.update(pk_val, data)
    except ValueError as e:
        msg = str(e)
        if 'Duplicate' in msg or 'UNIQUE' in msg:
            return JSONResponse({'error': msg}, status_code=409)
        return JSONResponse({'error': msg}, status_code=400)
    if result is None:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result


@pkg_router.delete('/entities/{entity_type}/{pk}')
def api_entity_delete(entity_type: str, pk: str,
                      conn: sqlite3.Connection = Depends(get_package_db)):
    """Delete an entity."""
    _require_admin()
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    if 'delete' not in schema.operations:
        return JSONResponse({'error': 'Delete not allowed'}, status_code=403)

    try:
        pk_val = int(pk)
    except ValueError:
        pk_val = pk
    engine = CrudEngine(conn, schema)
    deleted = engine.delete(pk_val)
    if not deleted:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return {'message': f'{entity_type} deleted', 'id': pk_val}


@pkg_router.post('/entities/{entity_type}/hooks/{hook_name}')
def api_entity_hook(entity_type: str, hook_name: str,
                    conn: sqlite3.Connection = Depends(get_package_db)):
    """Manually trigger a named hook."""
    _require_admin()
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    schema = schemas[entity_type]
    cursor = conn.cursor()
    for hook in schema.hooks:
        if hook.get('name') == hook_name:
            sql = hook.get('sql')
            if sql:
                cursor.execute(sql)
                conn.commit()
            return {'message': f'Hook {hook_name} executed'}
    return JSONResponse({'error': f'Hook not found: {hook_name}'}, status_code=404)


@pkg_router.get('/search/{entity_type}')
def api_entity_search(entity_type: str, request: Request, q: str = '',
                      conn: sqlite3.Connection = Depends(get_package_db)):
    """FK autocomplete search for an entity type."""
    schemas = _get_entity_schemas(conn)
    if entity_type not in schemas:
        return JSONResponse({'error': f'Entity type not found: {entity_type}'}, status_code=404)

    # Pass extra query params as column filters (exclude 'q')
    filters = {k: v for k, v in request.query_params.items() if k != 'q'}

    engine = CrudEngine(conn, schemas[entity_type])
    return engine.search(q, limit=20, filters=filters or None)


# ---------------------------------------------------------------------------
# Meta-package API endpoints (must come BEFORE the catch-all entity detail)
# ---------------------------------------------------------------------------

@pkg_router.get('/meta/tree')
def api_meta_tree(package: str):
    """Get meta_tree.json for a meta-package."""
    reg = get_registry()
    try:
        info = reg.get_package(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    if info.get('kind') != 'meta-package':
        raise HTTPException(status_code=400, detail="Not a meta-package")
    return info.get('meta_tree')


@pkg_router.get('/meta/bindings')
def api_meta_bindings(package: str):
    """Get package_bindings.json for a meta-package."""
    reg = get_registry()
    try:
        info = reg.get_package(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    if info.get('kind') != 'meta-package':
        raise HTTPException(status_code=400, detail="Not a meta-package")
    return info.get('package_bindings')


@pkg_router.get('/meta/composite-tree')
def api_meta_composite_tree(package: str, node_id: str = None):
    """Build composite tree from meta_tree + package bindings.

    If node_id is given, returns children of that node (lazy loading).
    If omitted, returns the full meta_tree with binding info.
    """
    reg = get_registry()
    try:
        info = reg.get_package(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    if info.get('kind') != 'meta-package':
        raise HTTPException(status_code=400, detail="Not a meta-package")

    meta_tree = info.get('meta_tree', {})
    bindings_data = info.get('package_bindings', {})
    nodes = meta_tree.get('nodes', [])

    # Index nodes
    node_map = {n['id']: n for n in nodes}

    # Index bindings by node_id
    binding_map = {}
    for b in bindings_data.get('bindings', []):
        binding_map.setdefault(b['node_id'], []).append(b)

    # Determine which member packages are available
    available = {p['name'] for p in reg.list_packages()}

    if node_id is None:
        # Return full tree structure
        result_nodes = []
        for n in nodes:
            children_ids = [c['id'] for c in nodes if c.get('parent') == n['id']]
            node_bindings = binding_map.get(n['id'], [])
            result = {
                'id': n['id'],
                'label': n['label'],
                'rank': n.get('rank', ''),
                'children': children_ids,
                'bindings': [],
            }
            for b in node_bindings:
                result['bindings'].append({
                    'package_id': b['package_id'],
                    'root_taxon': b['root_taxon'],
                    'available': b['package_id'] in available,
                    'source': b.get('source', ''),
                    'priority': b.get('priority', 99),
                })
            result['has_data'] = any(
                bi['available'] for bi in result['bindings']
            )
            result_nodes.append(result)
        return {'nodes': result_nodes}

    # Lazy load: expand a specific node's bindings
    if node_id not in node_map:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

    node_bindings = binding_map.get(node_id, [])
    children = []

    for b in sorted(node_bindings, key=lambda x: x.get('priority', 99)):
        pkg_id = b['package_id']
        if pkg_id not in available:
            continue
        root = b['root_taxon']
        try:
            conn = reg.get_db(pkg_id)
            cursor = conn.cursor()
            # Find root taxon id
            cursor.execute(
                "SELECT id FROM taxon WHERE name = ? AND rank = ?",
                (root['name'], root['rank'])
            )
            row = cursor.fetchone()
            if not row:
                conn.close()
                continue
            root_id = row['id']
            # Get children from default profile edge_cache
            cursor.execute("""
                SELECT t.id, t.name, t.rank,
                       (SELECT COUNT(*) FROM classification_edge_cache c2
                        WHERE c2.parent_id = t.id AND c2.profile_id = 1) as child_count
                FROM taxon t
                JOIN classification_edge_cache c ON c.child_id = t.id AND c.profile_id = 1
                WHERE c.parent_id = ?
                ORDER BY t.name
            """, (root_id,))
            for r in cursor.fetchall():
                children.append({
                    'package': pkg_id,
                    'taxon_id': r['id'],
                    'name': r['name'],
                    'rank': r['rank'],
                    'child_count': r['child_count'],
                })
            conn.close()
        except Exception as e:
            logger.warning("Error loading subtree from %s: %s", pkg_id, e)

    return {'node_id': node_id, 'children': children}


# ---------------------------------------------------------------------------
# Entity detail endpoint — serves manifest source URLs like /api/{pkg}/genus/123
# Runs {entity}_detail query + discovered sub-queries → composite JSON
# MUST be registered last in pkg_router: catch-all /{name}/{id} pattern.
# ---------------------------------------------------------------------------

@pkg_router.get('/{entity_name}/{entity_id}',
                responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_entity_detail(entity_name: str, entity_id: str,
                      conn: sqlite3.Connection = Depends(get_package_db)):
    """Resolve manifest source URLs (e.g. /api/{pkg}/genus/683).

    Executes the ``{entity}_detail`` named query and attaches results from
    sub-queries whose names start with ``{entity}_``.
    """
    detail_query = f'{entity_name}_detail'
    param_name = f'{entity_name}_id'

    result = _execute_query(conn, detail_query, {param_name: entity_id})
    if result is None:
        return JSONResponse({'error': f'Query not found: {detail_query}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    if result.get('row_count', 0) == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)

    data = dict(result['rows'][0])

    # Discover sub-queries: {entity}_* (excluding _detail itself)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, params_json FROM ui_queries WHERE name LIKE ? AND name != ?",
        (f'{entity_name}_%', detail_query))
    sub_queries = cursor.fetchall()

    for sq in sub_queries:
        sub_name = sq['name']
        # Derive the data key: "genus_hierarchy" → "hierarchy"
        data_key = sub_name[len(entity_name) + 1:]
        params_def = json.loads(sq['params_json']) if sq['params_json'] else {}
        params = {}
        for pn in params_def:
            if pn == param_name:
                params[pn] = entity_id
            elif pn in data:
                # param name found in main result — pass through
                params[pn] = data[pn]
            else:
                params[pn] = ''
        sub_result = _execute_query(conn, sub_name, params)
        if sub_result and 'rows' in sub_result:
            data[data_key] = sub_result['rows']

    return data


# ---------------------------------------------------------------------------
# Legacy fallback: /api/... (no package prefix) resolves to active or single package.
# MUST be included BEFORE pkg_router so /api/manifest doesn't match /api/{package}.
# This maintains backward compatibility with tests and single-package mode.
legacy_router = APIRouter(prefix="/api")


def get_legacy_db():
    """Resolve DB for legacy /api/... routes (no package in URL)."""
    from scoda_engine_core.scoda_package import get_active_package_name, get_db
    active = get_active_package_name()
    if active:
        try:
            conn = get_registry().get_db(active)
        except KeyError:
            conn = get_db()
    else:
        # Testing mode or single-package: use direct get_db()
        conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


# Re-register key endpoints under /api/ with legacy DB resolver
@legacy_router.get('/manifest')
def legacy_manifest(conn: sqlite3.Connection = Depends(get_legacy_db)):
    result = _fetch_manifest(conn)
    if result:
        result['mode'] = SCODA_MODE
        return result
    return JSONResponse({'error': 'No manifest found'}, status_code=404)

@legacy_router.get('/queries')
def legacy_queries(conn: sqlite3.Connection = Depends(get_legacy_db)):
    return _fetch_queries(conn)

@legacy_router.get('/queries/{query_name}/execute')
def legacy_query_execute(query_name: str, request: Request,
                         conn: sqlite3.Connection = Depends(get_legacy_db)):
    params = dict(request.query_params)
    result = _execute_query(conn, query_name, params)
    if result is None:
        return JSONResponse({'error': f'Query not found: {query_name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    return result

@legacy_router.get('/detail/{query_name}')
def legacy_detail(query_name: str, request: Request,
                  conn: sqlite3.Connection = Depends(get_legacy_db)):
    params = dict(request.query_params)
    result = _execute_query(conn, query_name, params)
    if result is None:
        return JSONResponse({'error': f'Query not found: {query_name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    if result['row_count'] == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result['rows'][0]

@legacy_router.get('/composite/{view_name}')
def legacy_composite(view_name: str, request: Request,
                     conn: sqlite3.Connection = Depends(get_legacy_db)):
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)
    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        return JSONResponse({'error': 'No manifest found'}, status_code=404)
    views = manifest_data['manifest'].get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        return JSONResponse({'error': f'Detail view not found: {view_name}'}, status_code=404)
    source_param = view.get('source_param', 'id')
    main_params = dict(request.query_params)
    main_params[source_param] = entity_id
    result = _execute_query(conn, view['source_query'], main_params)
    if result is None or result.get('row_count', 0) == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    data = dict(result['rows'][0])
    extra_params = dict(request.query_params)
    for key, sub_def in view.get('sub_queries', {}).items():
        params = dict(extra_params)
        for param_name, value_source in sub_def.get('params', {}).items():
            if value_source == 'id':
                params[param_name] = entity_id
            elif value_source.startswith('result.'):
                params[param_name] = data.get(value_source[7:], '')
            else:
                params[param_name] = value_source
        sub_result = _execute_query(conn, sub_def['query'], params)
        data[key] = sub_result['rows'] if sub_result and 'rows' in sub_result else []
    return data

@legacy_router.get('/preferences')
def legacy_preferences(conn: sqlite3.Connection = Depends(get_legacy_db)):
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM overlay.overlay_metadata WHERE key LIKE 'pref_%'")
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            k = r['key'][5:]
            try:
                result[k] = json.loads(r['value'])
            except (json.JSONDecodeError, TypeError):
                result[k] = r['value']
        return result
    except Exception:
        return {}

app.include_router(legacy_router)

# Package router AFTER legacy router
app.include_router(pkg_router)


# ---------------------------------------------------------------------------
# Global endpoints (package-independent)
# ---------------------------------------------------------------------------

@app.get('/api/packages')
def api_packages():
    """List all available packages."""
    return get_registry().list_packages()


@app.get('/healthz')
def healthz():
    """Health check endpoint."""
    packages = get_registry().list_packages()
    return {
        "status": "ok",
        "engine_version": ENGINE_VERSION,
        "engine_name": ENGINE_NAME,
        "mode": SCODA_MODE,
        "packages": len(packages),
    }


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    """Landing page — redirect to single/top-level package or show landing."""
    packages = get_registry().list_packages()

    # SCODA_PACKAGE env var: redirect to specific package
    env_pkg = os.environ.get('SCODA_PACKAGE')
    if env_pkg:
        return RedirectResponse(url=f'/{env_pkg}/', status_code=302)

    # Single package: redirect
    if len(packages) == 1:
        return RedirectResponse(url=f'/{packages[0]["name"]}/', status_code=302)

    # Multiple packages: find top-level (not a dependency of any other package)
    if len(packages) > 1:
        # Collect all names that appear as a dependency of another package
        dep_names = set()
        for p in packages:
            for d in p.get('deps', []):
                dep_names.add(d.get('name', ''))
        # Top-level = not depended on by anyone
        top_level = [p for p in packages if p['name'] not in dep_names]
        if len(top_level) == 1:
            return RedirectResponse(url=f'/{top_level[0]["name"]}/', status_code=302)
        # Show only top-level/independent packages on landing
        if top_level:
            # Store filtered list for landing page to use
            pass  # landing.html fetches /api/packages, filtering done client-side

    # Multiple top-level packages (or zero): landing page
    return templates.TemplateResponse(request, "landing.html", {
        "cache_bust": int(time.time()),
    })


@app.get('/{package}/', response_class=HTMLResponse, include_in_schema=False)
@app.get('/{package}', response_class=HTMLResponse)
def package_index(request: Request, package: str):
    """Package viewer page (with or without trailing slash)."""
    # Verify package exists in registry
    try:
        get_registry().get_package(package)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Package not found: {package}")
    return templates.TemplateResponse(request, "index.html", {
        "cache_bust": int(time.time()),
        "package_name": package,
    })


# ---------------------------------------------------------------------------
# Mount MCP SSE server as sub-application at /mcp (opt-in via SCODA_ENABLE_MCP=1)
# ---------------------------------------------------------------------------
if os.environ.get('SCODA_ENABLE_MCP') == '1':
    from .mcp_server import create_mcp_app
    app.mount("/mcp", create_mcp_app())


if __name__ == '__main__':
    import argparse
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=str, default=None,
                        help='Active package name')
    parser.add_argument('--scoda-path', type=str, default=None,
                        help='Path to a .scoda file to load')
    parser.add_argument('--port', type=int, default=8080,
                        help='Server port (default: 8080)')
    args = parser.parse_args()
    if args.scoda_path:
        from scoda_engine_core import register_scoda_path
        register_scoda_path(args.scoda_path)
    elif args.package:
        from scoda_engine_core import set_active_package
        set_active_package(args.package)
    uvicorn.run(app, host='0.0.0.0', port=args.port)
