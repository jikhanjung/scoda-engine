import sqlite3
import os
import sys
import re
import argparse
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
import json
import asyncio
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
import uvicorn

logger = logging.getLogger(__name__)

from scoda_engine_core import get_db, ensure_overlay_db, get_mcp_tools

def row_to_dict(row):
    return dict(row)

# ---------------------------------------------------------------------------
# SQL validation for dynamic tools
# ---------------------------------------------------------------------------

_FORBIDDEN_SQL = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM|REINDEX)\b',
    re.IGNORECASE
)


def _validate_sql(sql):
    """Validate that SQL is a read-only SELECT/WITH statement.

    Raises ValueError if SQL contains forbidden keywords.
    """
    stripped = sql.strip()
    if not stripped.upper().startswith(('SELECT', 'WITH')):
        raise ValueError(f"SQL must start with SELECT or WITH, got: {stripped[:30]!r}")
    if _FORBIDDEN_SQL.search(stripped):
        match = _FORBIDDEN_SQL.search(stripped)
        raise ValueError(f"Forbidden SQL keyword: {match.group()}")


# ---------------------------------------------------------------------------
# Internal query helpers (use existing conn, no open/close)
# ---------------------------------------------------------------------------

def _execute_named_query_internal(conn, query_name, params=None):
    """Execute a named query from ui_queries. Returns result dict or error dict."""
    cursor = conn.cursor()
    if params is None:
        params = {}

    cursor.execute("SELECT sql, params_json FROM ui_queries WHERE name = ?", (query_name,))
    query_row = cursor.fetchone()
    if not query_row:
        logger.warning("Named query not found: %s", query_name)
        return {"error": f"Named query '{query_name}' not found."}

    sql_query = query_row['sql']
    db_params = json.loads(query_row['params_json']) if query_row['params_json'] else {}
    merged_params = {**db_params, **params}

    try:
        cursor.execute(sql_query, merged_params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        logger.debug("Named query '%s' returned %d rows", query_name, len(rows))
        return {
            'query': query_name,
            'columns': columns,
            'row_count': len(rows),
            'rows': [row_to_dict(row) for row in rows]
        }
    except Exception as e:
        logger.error("Named query '%s' failed: %s", query_name, e)
        return {"error": f"Error executing named query '{query_name}': {str(e)}"}


def _execute_composite_for_mcp(conn, view_name, entity_id):
    """Execute a composite detail query (same logic as app.py composite endpoint).

    Reads the manifest, finds the view definition, executes source_query + sub_queries,
    and returns a merged dict.
    """
    cursor = conn.cursor()

    # Read manifest
    cursor.execute("SELECT manifest_json FROM ui_manifest WHERE name = 'default'")
    row = cursor.fetchone()
    if not row:
        return {"error": "No manifest found"}

    manifest = json.loads(row['manifest_json'])
    views = manifest.get('views', {})
    view = views.get(view_name)
    if not view or view.get('type') != 'detail' or 'source_query' not in view:
        return {"error": f"Detail view not found: {view_name}"}

    # Main query
    source_param = view.get('source_param', 'id')
    result = _execute_named_query_internal(conn, view['source_query'], {source_param: entity_id})
    if result is None or result.get('row_count', 0) == 0:
        return {"error": "Not found"}
    if 'error' in result:
        return result

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
        sub_result = _execute_named_query_internal(conn, sub_def['query'], params)
        data[key] = sub_result['rows'] if sub_result and 'rows' in sub_result else []

    return data


# ---------------------------------------------------------------------------
# Dynamic tool execution
# ---------------------------------------------------------------------------

def _execute_dynamic_tool(tool_def, arguments):
    """Execute a dynamically defined MCP tool based on its query_type.

    Returns a result dict suitable for JSON serialization.
    """
    query_type = tool_def.get('query_type')
    logger.debug("Dynamic tool: query_type=%s", query_type)
    conn = get_db()

    try:
        if query_type == 'single':
            sql = tool_def['sql']
            _validate_sql(sql)

            # Build params from arguments + defaults
            params = dict(tool_def.get('default_params', {}))
            params.update(arguments)

            cursor = conn.cursor()
            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return {
                'columns': columns,
                'row_count': len(rows),
                'rows': [row_to_dict(row) for row in rows]
            }

        elif query_type == 'named_query':
            named_query = tool_def['named_query']
            # Map input arguments to query params
            param_mapping = tool_def.get('param_mapping', {})
            params = {}
            for query_param, input_key in param_mapping.items():
                if input_key in arguments:
                    params[query_param] = arguments[input_key]
            return _execute_named_query_internal(conn, named_query, params)

        elif query_type == 'composite':
            view_name = tool_def['view_name']
            param_mapping = tool_def.get('param_mapping', {})
            # Get the entity_id from the first mapped param
            entity_id = None
            for query_param, input_key in param_mapping.items():
                if input_key in arguments:
                    entity_id = arguments[input_key]
                    break
            if entity_id is None:
                return {"error": "Missing required entity ID parameter"}
            return _execute_composite_for_mcp(conn, view_name, entity_id)

        else:
            return {"error": f"Unknown query_type: {query_type}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Built-in tool handler functions
# ---------------------------------------------------------------------------

def execute_named_query(query_name: str, params: dict = None) -> list[dict] | dict:
    """Execute a predefined named SQL query from the ui_queries table."""
    conn = get_db()
    result = _execute_named_query_internal(conn, query_name, params)
    conn.close()
    return result

def get_annotations(entity_type: str, entity_id: int) -> list[dict]:
    """Retrieve user annotations for a specific entity."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, entity_type, entity_id, entity_name, annotation_type, content, author, created_at
        FROM overlay.user_annotations
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY created_at DESC, id DESC
    """, (entity_type, entity_id))
    annotations = [row_to_dict(row) for row in cursor.fetchall()]
    conn.close()
    return annotations

def add_annotation(entity_type: str, entity_id: int, entity_name: str, annotation_type: str, content: str, author: str = None) -> dict:
    """Add a new user annotation to an entity. This writes to the local overlay database."""
    conn = get_db()
    cursor = conn.cursor()

    if not entity_type:
        return {"error": "entity_type is required"}

    if not annotation_type:
        return {"error": "annotation_type is required"}

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
    annotation = row_to_dict(cursor.fetchone())
    conn.close()

    return annotation

def delete_annotation(annotation_id: int) -> dict:
    """Delete a user annotation by its ID."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    if not cursor.fetchone():
        conn.close()
        return {"error": f"Annotation with ID {annotation_id} not found."}

    cursor.execute("DELETE FROM overlay.user_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    conn.close()
    return {"message": f"Annotation with ID {annotation_id} deleted."}

def get_provenance() -> list[dict]:
    """Get data provenance information."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, source_type, citation, description, year, url
        FROM provenance
        ORDER BY id
    """)
    sources = cursor.fetchall()

    conn.close()

    return [row_to_dict(s) for s in sources]

def list_available_queries() -> list[dict]:
    """Get list of available named queries."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, description, params_json, created_at
        FROM ui_queries
        ORDER BY name
    """)
    queries = cursor.fetchall()
    conn.close()

    return [row_to_dict(q) for q in queries]


# ---------------------------------------------------------------------------
# Built-in tools (always provided, regardless of mcp_tools.json)
# ---------------------------------------------------------------------------

_BUILTIN_TOOL_NAMES = {
    'execute_named_query', 'list_available_queries',
    'get_metadata', 'get_provenance',
    'get_annotations', 'add_annotation', 'delete_annotation',
}


def _get_builtin_tools():
    """Return the 7 built-in Tool definitions (generic, not domain-specific)."""
    return [
        Tool(
            name="execute_named_query",
            description="Execute a predefined named SQL query from the ui_queries table.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_name": {"type": "string", "description": "The name of the query to execute (see /api/queries for available names)."},
                    "params": {"type": "object", "description": "A dictionary of parameters to pass to the query.", "additionalProperties": True, "default": {}}
                },
                "required": ["query_name"]
            }
        ),
        Tool(
            name="list_available_queries",
            description="List all available named queries stored in the database.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_metadata",
            description="Get SCODA artifact metadata (name, version, license, etc.).",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_provenance",
            description="Get provenance information about the data sources.",
            inputSchema={"type": "object", "properties": {}, "required": []}
        ),
        Tool(
            name="get_annotations",
            description="Retrieve user annotations for a specific entity (genus, family, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "The type of entity (e.g., 'genus', 'family', 'order')."},
                    "entity_id": {"type": "integer", "description": "The ID of the entity."}
                },
                "required": ["entity_type", "entity_id"]
            }
        ),
        Tool(
            name="add_annotation",
            description="Add a new user annotation to an entity. This writes to the local overlay database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_type": {"type": "string", "description": "The type of entity (e.g., 'genus', 'family', 'order')."},
                    "entity_id": {"type": "integer", "description": "The ID of the entity."},
                    "entity_name": {"type": "string", "description": "The name of the entity for matching across releases."},
                    "annotation_type": {"type": "string", "description": "The type of annotation (e.g., 'note', 'correction', 'alternative', 'link')."},
                    "content": {"type": "string", "description": "The content of the annotation."},
                    "author": {"type": "string", "description": "Optional: The author of the annotation."}
                },
                "required": ["entity_type", "entity_id", "entity_name", "annotation_type", "content"]
            }
        ),
        Tool(
            name="delete_annotation",
            description="Delete a user annotation by its ID.",
            inputSchema={
                "type": "object",
                "properties": {"annotation_id": {"type": "integer", "description": "The ID of the annotation to delete."}},
                "required": ["annotation_id"]
            }
        ),
    ]


# ---------------------------------------------------------------------------
# Dynamic tools (loaded from mcp_tools.json in .scoda package)
# ---------------------------------------------------------------------------

def _get_dynamic_tools():
    """Load MCP tools from the active package's mcp_tools.json.

    Returns a list of Tool objects, or empty list if no mcp_tools.json.
    """
    mcp_tools_data = get_mcp_tools()
    if not mcp_tools_data:
        return []

    tools = []
    for tool_def in mcp_tools_data.get('tools', []):
        tools.append(Tool(
            name=tool_def['name'],
            description=tool_def.get('description', ''),
            inputSchema=tool_def.get('input_schema', {"type": "object", "properties": {}, "required": []})
        ))
    return tools


def _get_dynamic_tool_defs():
    """Return the raw tool definitions from mcp_tools.json (for call_tool dispatch)."""
    mcp_tools_data = get_mcp_tools()
    if not mcp_tools_data:
        return {}
    return {t['name']: t for t in mcp_tools_data.get('tools', [])}


# ---------------------------------------------------------------------------
# MCP Server setup
# ---------------------------------------------------------------------------

app = Server("scoda-desktop")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return available MCP tools: builtin + dynamic."""
    builtin = _get_builtin_tools()
    dynamic = _get_dynamic_tools()
    return builtin + dynamic


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls — dispatch to builtin handler or dynamic executor."""
    logger.info("MCP call_tool: %s(%s)", name, ", ".join(f"{k}={v!r}" for k, v in arguments.items()) if arguments else "")

    # --- Built-in tools ---
    if name == "execute_named_query":
        query_name = arguments.get("query_name")
        params = arguments.get("params")
        result = execute_named_query(query_name, params)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_metadata":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM artifact_metadata")
        metadata = {row['key']: row['value'] for row in cursor.fetchall()}
        conn.close()
        return [TextContent(type="text", text=json.dumps(metadata, indent=2))]
    elif name == "get_provenance":
        result = get_provenance()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "list_available_queries":
        result = list_available_queries()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "get_annotations":
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")
        annotations = get_annotations(entity_type, entity_id)
        return [TextContent(type="text", text=json.dumps(annotations, indent=2))]
    elif name == "add_annotation":
        entity_type = arguments.get("entity_type")
        entity_id = arguments.get("entity_id")
        entity_name = arguments.get("entity_name")
        annotation_type = arguments.get("annotation_type")
        content = arguments.get("content")
        author = arguments.get("author")
        result = add_annotation(entity_type, entity_id, entity_name, annotation_type, content, author)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "delete_annotation":
        annotation_id = arguments.get("annotation_id")
        result = delete_annotation(annotation_id)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # --- Dynamic tools (from mcp_tools.json) ---
    dynamic_defs = _get_dynamic_tool_defs()
    if name in dynamic_defs:
        result = _execute_dynamic_tool(dynamic_defs[name], arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # Fallback for unknown tools
    logger.warning("Unknown MCP tool requested: %s", name)
    return [TextContent(type="text", text=json.dumps({"error": f"Tool '{name}' not implemented."}))]

async def run_stdio():
    """Run MCP server in stdio mode (for Claude Desktop spawning)."""
    ensure_overlay_db()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

def create_mcp_app() -> Starlette:
    """Create MCP SSE Starlette app for mounting or standalone use."""
    ensure_overlay_db()

    sse = SseServerTransport("/messages")

    async def handle_sse(request):
        """Handle SSE connections."""
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )
        return Response()

    async def handle_messages(request):
        """Handle message POST requests."""
        return await sse.handle_post_message(request.scope, request.receive, request._send)

    async def health_check(request):
        """Simple health check endpoint."""
        return Response(
            content=json.dumps({
                "status": "ok",
                "service": "scoda-desktop-mcp",
                "mode": "sse"
            }),
            media_type="application/json"
        )

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
            Route("/health", endpoint=health_check),
        ]
    )


def run_sse(host: str = "localhost", port: int = 8081):
    """Run MCP server in SSE mode (HTTP server for persistent connections)."""
    starlette_app = create_mcp_app()

    logger.info("MCP Server (SSE mode) starting on http://%s:%d", host, port)
    logger.info("   SSE endpoint: http://%s:%d/sse", host, port)
    logger.info("   Health check: http://%s:%d/health", host, port)

    uvicorn.run(starlette_app, host=host, port=port, log_level="info")

def main():
    """Main entry point - parse args and run in appropriate mode."""
    parser = argparse.ArgumentParser(description="SCODA Desktop MCP Server")
    parser.add_argument(
        "--mode",
        choices=["stdio", "sse"],
        default="stdio",
        help="Server mode: stdio (for Claude Desktop) or sse (HTTP server)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind SSE server to (SSE mode only)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port for SSE server (SSE mode only)"
    )

    args = parser.parse_args()

    if args.mode == "stdio":
        asyncio.run(run_stdio())
    else:
        # SSE mode runs synchronously with uvicorn
        run_sse(args.host, args.port)

if __name__ == "__main__":
    main()
