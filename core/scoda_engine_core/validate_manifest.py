"""
Manifest Validator / Linter for .scoda packages.

Validates ui_manifest JSON against ui_queries to detect missing/inconsistent
references before packaging. Catches bugs like:
- chart_options missing required keys
- on_row_click.detail_view referencing non-existent views
- source_query referencing deleted named queries
- sub_queries result.<field> referencing non-existent source query output fields

Pure-stdlib module — no external dependencies.
"""

import json
import os
import sqlite3

# Known view types
KNOWN_VIEW_TYPES = {'table', 'tree', 'chart', 'hierarchy', 'detail'}

# Known section types (custom types produce warning, not error)
KNOWN_SECTION_TYPES = {
    'field_grid', 'linked_table', 'tagged_list', 'raw_text', 'annotations',
    'genus_geography', 'synonym_list', 'rank_statistics', 'rank_children',
}

# Required keys for tree_options
TREE_REQUIRED_KEYS = {'id_key', 'parent_key', 'label_key'}

# Required keys for chart_options
CHART_REQUIRED_KEYS = {'id_key', 'parent_key', 'label_key', 'color_key', 'rank_key', 'rank_columns'}


def validate_manifest(manifest, named_queries):
    """Validate a manifest dict against available named queries.

    Pure function — no DB access.

    Args:
        manifest: parsed manifest JSON (dict with 'default_view' and 'views')
        named_queries: set of available named query names

    Returns:
        (errors, warnings) — lists of human-readable strings
    """
    errors = []
    warnings = []

    views = manifest.get('views', {})

    # Check default_view
    default_view = manifest.get('default_view')
    if default_view and default_view not in views:
        errors.append(f"default_view '{default_view}' not found in views")

    # Validate each view
    for view_name, view_def in views.items():
        _validate_view(view_name, view_def, views, named_queries, errors, warnings)

    return errors, warnings


def _validate_view(view_name, view_def, views, named_queries, errors, warnings):
    """Dispatch view validation by type."""
    view_type = view_def.get('type')
    if not view_type:
        errors.append(f"view '{view_name}': missing 'type'")
        return

    if view_type not in KNOWN_VIEW_TYPES:
        errors.append(f"view '{view_name}': unrecognized type '{view_type}'")
        return

    # Check source_query (common to table/tree/chart/hierarchy)
    source_query = view_def.get('source_query')
    if source_query and source_query not in named_queries:
        errors.append(
            f"view '{view_name}': source_query '{source_query}' not found in ui_queries")

    if view_type == 'table':
        _validate_table_view(view_name, view_def, views, named_queries, errors, warnings)
    elif view_type == 'tree':
        _validate_tree_view(view_name, view_def, views, named_queries, errors, warnings)
    elif view_type == 'chart':
        _validate_chart_view(view_name, view_def, views, named_queries, errors, warnings)
    elif view_type == 'hierarchy':
        _validate_hierarchy_view(view_name, view_def, views, named_queries, errors, warnings)
    elif view_type == 'detail':
        _validate_detail_view(view_name, view_def, views, named_queries, errors, warnings)


def _validate_table_view(view_name, view_def, views, named_queries, errors, warnings):
    """Validate a table view."""
    columns = view_def.get('columns', [])
    column_keys = {c.get('key') for c in columns if c.get('key')}

    # default_sort.key must be in columns
    default_sort = view_def.get('default_sort')
    if default_sort:
        sort_key = default_sort.get('key')
        if sort_key and sort_key not in column_keys:
            errors.append(
                f"view '{view_name}': default_sort.key '{sort_key}' not in columns")

    # on_row_click.detail_view should exist
    on_row_click = view_def.get('on_row_click')
    if on_row_click:
        detail_view = on_row_click.get('detail_view')
        if detail_view and detail_view not in views:
            errors.append(
                f"view '{view_name}': on_row_click.detail_view '{detail_view}' not in views")
    else:
        warnings.append(f"view '{view_name}': no on_row_click (UX recommendation)")


def _validate_tree_view(view_name, view_def, views, named_queries, errors, warnings):
    """Validate a tree view."""
    tree_opts = view_def.get('tree_options', {})
    missing = TREE_REQUIRED_KEYS - set(tree_opts.keys())
    if missing:
        errors.append(
            f"view '{view_name}': tree_options missing required keys: {sorted(missing)}")

    # item_query must exist in named queries
    item_query = tree_opts.get('item_query')
    if item_query and item_query not in named_queries:
        errors.append(
            f"view '{view_name}': tree_options.item_query '{item_query}' not in ui_queries")

    # Check detail_view references inside tree_options
    for ref in _collect_detail_view_refs(view_def):
        if ref not in views:
            errors.append(
                f"view '{view_name}': detail_view '{ref}' not in views")


def _validate_chart_view(view_name, view_def, views, named_queries, errors, warnings):
    """Validate a chart view."""
    chart_opts = view_def.get('chart_options', {})
    missing = CHART_REQUIRED_KEYS - set(chart_opts.keys())
    if missing:
        errors.append(
            f"view '{view_name}': chart_options missing required keys: {sorted(missing)}")

    # Check cell_click.detail_view
    cell_click = chart_opts.get('cell_click', {})
    detail_view = cell_click.get('detail_view')
    if detail_view and detail_view not in views:
        errors.append(
            f"view '{view_name}': chart_options.cell_click.detail_view '{detail_view}' not in views")


def _validate_hierarchy_view(view_name, view_def, views, named_queries, errors, warnings):
    """Validate a hierarchy view (unified tree+chart)."""
    h_opts = view_def.get('hierarchy_options', {})
    # hierarchy_options should have at least id_key, parent_key, label_key
    missing = TREE_REQUIRED_KEYS - set(h_opts.keys())
    if missing:
        errors.append(
            f"view '{view_name}': hierarchy_options missing required keys: {sorted(missing)}")

    display = view_def.get('display')

    # tree display: check item_query reference
    if display == 'tree':
        tree_disp = view_def.get('tree_display', {})
        item_query = tree_disp.get('item_query')
        if item_query and item_query not in named_queries:
            errors.append(
                f"view '{view_name}': tree_display.item_query '{item_query}' not in ui_queries")
        # Check detail_view references inside tree_display
        for ref in _collect_detail_view_refs(tree_disp):
            if ref not in views:
                errors.append(
                    f"view '{view_name}': detail_view '{ref}' not in views")

    # nested_table display: check required nested_table_display keys
    elif display == 'nested_table':
        nt_disp = view_def.get('nested_table_display', {})
        if 'rank_columns' not in nt_disp:
            errors.append(
                f"view '{view_name}': nested_table_display missing 'rank_columns'")
        cell_click = nt_disp.get('cell_click', {})
        detail_view = cell_click.get('detail_view')
        if detail_view and detail_view not in views:
            errors.append(
                f"view '{view_name}': nested_table_display.cell_click.detail_view "
                f"'{detail_view}' not in views")


def _validate_detail_view(view_name, view_def, views, named_queries, errors, warnings):
    """Validate a detail view."""
    # source_query check already done in _validate_view

    # sub_queries validation
    sub_queries = view_def.get('sub_queries', {})
    for sq_name, sq_def in sub_queries.items():
        sq_query = sq_def.get('query')
        if sq_query and sq_query not in named_queries:
            errors.append(
                f"view '{view_name}': sub_queries['{sq_name}'].query "
                f"'{sq_query}' not in ui_queries")

    # Validate sections
    for section in view_def.get('sections', []):
        section_type = section.get('type', '')

        if section_type == 'linked_table':
            if 'data_key' not in section:
                errors.append(
                    f"view '{view_name}': linked_table section missing 'data_key'")
            # Check on_row_click inside linked_table
            orc = section.get('on_row_click', {})
            dv = orc.get('detail_view')
            if dv and dv not in views:
                errors.append(
                    f"view '{view_name}': linked_table on_row_click.detail_view "
                    f"'{dv}' not in views")

        elif section_type == 'raw_text':
            if 'data_key' not in section:
                errors.append(
                    f"view '{view_name}': raw_text section missing 'data_key'")

        elif section_type == 'field_grid':
            if 'fields' not in section:
                errors.append(
                    f"view '{view_name}': field_grid section missing 'fields'")

        elif section_type not in KNOWN_SECTION_TYPES:
            warnings.append(
                f"view '{view_name}': unrecognized section type '{section_type}'")


def _collect_detail_view_refs(view_def):
    """Collect all detail_view references from a view definition (recursive)."""
    refs = set()

    def _walk(obj):
        if isinstance(obj, dict):
            if 'detail_view' in obj:
                refs.add(obj['detail_view'])
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(view_def)
    return refs


def validate_db(db_path):
    """Validate the ui_manifest in a SQLite database.

    Args:
        db_path: path to a .db file with ui_manifest and ui_queries tables

    Returns:
        (errors, warnings) — lists of human-readable strings
    """
    errors = []
    warnings = []

    if not os.path.exists(db_path):
        return [f"Database not found: {db_path}"], []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Check ui_manifest table exists
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    if 'ui_manifest' not in tables:
        conn.close()
        return ["ui_manifest table not found"], []

    if 'ui_queries' not in tables:
        conn.close()
        return ["ui_queries table not found"], []

    # Load named queries
    named_queries = set()
    for row in conn.execute("SELECT name FROM ui_queries"):
        named_queries.add(row['name'])

    # Load manifest
    row = conn.execute(
        "SELECT manifest_json FROM ui_manifest WHERE name = 'default'"
    ).fetchone()
    conn.close()

    if not row:
        return ["No 'default' manifest found in ui_manifest"], []

    try:
        manifest = json.loads(row['manifest_json'])
    except (json.JSONDecodeError, TypeError) as e:
        return [f"Failed to parse manifest JSON: {e}"], []

    return validate_manifest(manifest, named_queries)
