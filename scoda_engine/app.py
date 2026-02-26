"""
SCODA Desktop Web Interface
FastAPI application for browsing SCODA data packages
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Optional
import json
import logging
import os
import sqlite3

logger = logging.getLogger(__name__)

from scoda_engine_core import get_db
from scoda_engine import __version__ as ENGINE_VERSION

app = FastAPI(title="SCODA Desktop")

# Tables that are SCODA metadata — excluded from auto-discovery
SCODA_META_TABLES = {'artifact_metadata', 'provenance', 'schema_descriptions',
                     'ui_display_intent', 'ui_queries', 'ui_manifest'}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
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
# Core helper functions (shared by legacy and namespaced routes)
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
# Generic detail endpoint (named query → first row as flat JSON)
# ---------------------------------------------------------------------------

@app.get('/api/detail/{query_name}',
         responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_generic_detail(query_name: str, request: Request):
    """Execute a named query and return the first row as flat JSON."""
    conn = get_db()
    params = dict(request.query_params)
    result = _execute_query(conn, query_name, params)
    conn.close()
    if result is None:
        return JSONResponse({'error': f'Query not found: {query_name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    if result['row_count'] == 0:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return result['rows'][0]


@app.get('/api/composite/{view_name}',
         responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def api_composite_detail(view_name: str, request: Request):
    """Execute manifest-defined composite detail query."""
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)

    conn = get_db()
    manifest_data = _fetch_manifest(conn)
    if not manifest_data:
        conn.close()
        return JSONResponse({'error': 'No manifest found'}, status_code=404)

    views = manifest_data['manifest'].get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        logger.warning("Composite detail view not found: %s", view_name)
        conn.close()
        return JSONResponse({'error': f'Detail view not found: {view_name}'}, status_code=404)

    # Main query
    source_param = view.get('source_param', 'id')
    result = _execute_query(conn, view['source_query'], {source_param: entity_id})
    if result is None or result.get('row_count', 0) == 0:
        conn.close()
        return JSONResponse({'error': 'Not found'}, status_code=404)
    if 'error' in result:
        conn.close()
        return JSONResponse(result, status_code=400)

    data = dict(result['rows'][0])

    # Sub-queries
    for key, sub_def in view.get('sub_queries', {}).items():
        params = {}
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

    conn.close()
    return data



@app.get('/api/auto/detail/{table_name}',
         responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def api_auto_detail(table_name: str, request: Request):
    """Auto-generated detail: SELECT * FROM table WHERE pk = :id."""
    entity_id = request.query_params.get('id')
    if not entity_id:
        return JSONResponse({'error': 'id parameter required'}, status_code=400)

    conn = get_db()
    cursor = conn.cursor()

    # Block access to SCODA metadata tables
    if table_name in SCODA_META_TABLES:
        conn.close()
        return JSONResponse({'error': 'Metadata tables not accessible'}, status_code=403)

    # Verify table exists (SQL injection prevention)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if not cursor.fetchone():
        conn.close()
        return JSONResponse({'error': f'Table not found: {table_name}'}, status_code=404)

    # Find PK column
    cols_info = cursor.execute(f"PRAGMA table_info([{table_name}])").fetchall()
    pk_col = next((c[1] for c in cols_info if c[5]), 'id')

    try:
        cursor.execute(f"SELECT * FROM [{table_name}] WHERE [{pk_col}] = ?", (entity_id,))
        row = cursor.fetchone()
    except Exception as e:
        conn.close()
        return JSONResponse({'error': str(e)}, status_code=400)

    conn.close()
    if not row:
        return JSONResponse({'error': 'Not found'}, status_code=404)
    return dict(row)


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    """Main page — generic viewer."""
    return templates.TemplateResponse(request, "index.html")



@app.get('/api/provenance', response_model=list[ProvenanceItem])
def api_provenance():
    """Get data provenance information"""
    conn = get_db()
    result = _fetch_provenance(conn)
    conn.close()
    return result


@app.get('/api/display-intent', response_model=list[DisplayIntentItem])
def api_display_intent():
    """Get display intent hints for SCODA viewers"""
    conn = get_db()
    result = _fetch_display_intent(conn)
    conn.close()
    return result


@app.get('/api/queries', response_model=list[QueryItem])
def api_queries():
    """Get list of available named queries"""
    conn = get_db()
    result = _fetch_queries(conn)
    conn.close()
    return result


@app.get('/api/manifest', response_model=ManifestResponse,
         responses={404: {"model": ErrorResponse}})
def api_manifest():
    """Get UI manifest with declarative view definitions"""
    conn = get_db()
    result = _fetch_manifest(conn)
    conn.close()
    if result:
        return result
    return JSONResponse({'error': 'No manifest found'}, status_code=404)


@app.get('/api/queries/{name}/execute', response_model=QueryResult,
         responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_query_execute(name: str, request: Request):
    """Execute a named query with optional parameters"""
    conn = get_db()
    params = dict(request.query_params)
    result = _execute_query(conn, name, params)
    conn.close()
    if result is None:
        return JSONResponse({'error': f'Query not found: {name}'}, status_code=404)
    if 'error' in result:
        return JSONResponse(result, status_code=400)
    return result



@app.get('/api/annotations/{entity_type}/{entity_id}', response_model=list[AnnotationItem])
def api_get_annotations(entity_type: str, entity_id: int):
    """Get annotations for a specific entity"""
    conn = get_db()
    result = _fetch_annotations(conn, entity_type, entity_id)
    conn.close()
    return result


class AnnotationCreate(BaseModel):
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    entity_name: Optional[str] = None
    annotation_type: Optional[str] = None
    content: Optional[str] = None
    author: Optional[str] = None


@app.post('/api/annotations', status_code=201,
          responses={201: {"model": AnnotationItem}, 400: {"model": ErrorResponse}})
def api_create_annotation(body: AnnotationCreate):
    """Create a new annotation"""
    data = body.model_dump()
    conn = get_db()
    result, status = _create_annotation(conn, data)
    conn.close()
    return JSONResponse(result, status_code=status)


@app.delete('/api/annotations/{annotation_id}',
            responses={200: {"model": DeleteResponse}, 404: {"model": ErrorResponse}})
def api_delete_annotation(annotation_id: int):
    """Delete an annotation"""
    conn = get_db()
    result, status = _delete_annotation(conn, annotation_id)
    conn.close()
    return JSONResponse(result, status_code=status)


# ---------------------------------------------------------------------------
# Entity detail endpoint — serves manifest source URLs like /api/{entity}/123
# Runs {entity}_detail query + discovered sub-queries → composite JSON
# MUST be registered last: catch-all /api/{name}/{id} pattern.
# ---------------------------------------------------------------------------

@app.get('/api/{entity_name}/{entity_id}',
         responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def api_entity_detail(entity_name: str, entity_id: str):
    """Resolve manifest source URLs (e.g. /api/genus/683).

    Executes the ``{entity}_detail`` named query and attaches results from
    sub-queries whose names start with ``{entity}_``.
    """
    detail_query = f'{entity_name}_detail'
    param_name = f'{entity_name}_id'

    conn = get_db()
    result = _execute_query(conn, detail_query, {param_name: entity_id})
    if result is None:
        conn.close()
        return JSONResponse({'error': f'Query not found: {detail_query}'}, status_code=404)
    if 'error' in result:
        conn.close()
        return JSONResponse(result, status_code=400)
    if result.get('row_count', 0) == 0:
        conn.close()
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

    conn.close()
    return data


# Mount MCP SSE server as sub-application at /mcp
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
