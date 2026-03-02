"""
Shared test fixtures for SCODA Engine test suite.

Generic fixtures (no domain-specific data):
  - generic_db: categories/items/references + SCODA core tables
  - generic_client: TestClient wired to generic_db
  - generic_dep_db: dependency DB with regions/locations/entries
  - generic_dep_client: TestClient with generic_db + dep alias
  - generic_mcp_tools_data: mcp_tools.json dict for items/category_tree
  - generic_scoda_with_mcp_tools: .scoda with mcp_tools.json
  - no_manifest_db / no_manifest_client: plain DB without manifest
"""

import json
import sqlite3
import os
import sys

import pytest

import scoda_engine_core as scoda_package
# Enable MCP mount for tests (MCP is opt-in via SCODA_ENABLE_MCP)
os.environ.setdefault('SCODA_ENABLE_MCP', '1')
from scoda_engine.app import app
from scoda_engine_core import get_db, ScodaPackage

# Import overlay DB init (used by generic_db fixture)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))
from init_overlay_db import create_overlay_db


@pytest.fixture
def anyio_backend():
    return 'asyncio'

# OLD test_db fixture removed — replaced by generic_db
# OLD client fixture removed — replaced by generic_client
# OLD mcp_tools_data fixture removed — replaced by generic_mcp_tools_data
# OLD scoda_with_mcp_tools fixture removed — replaced by generic_scoda_with_mcp_tools

@pytest.fixture
def no_manifest_db(tmp_path):
    """Create a minimal DB with data tables but NO ui_manifest/ui_queries/SCODA metadata.

    This simulates opening a plain SQLite database that has no SCODA packaging.
    """
    db_path = str(tmp_path / "plain.db")
    overlay_path = str(tmp_path / "plain_overlay.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE species (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            genus TEXT,
            habitat TEXT,
            is_extinct INTEGER DEFAULT 0
        );
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (1, 'Paradoxides davidis', 'Paradoxides', 'Marine', 1);
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (2, 'Phacops rana', 'Phacops', 'Marine', 1);
        INSERT INTO species (id, name, genus, habitat, is_extinct)
        VALUES (3, 'Elrathia kingii', 'Elrathia', 'Marine', 1);

        CREATE TABLE localities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT,
            latitude REAL,
            longitude REAL
        );
        INSERT INTO localities (id, name, country, latitude, longitude)
        VALUES (1, 'Burgess Shale', 'Canada', 51.4, -116.5);
        INSERT INTO localities (id, name, country, latitude, longitude)
        VALUES (2, 'Wheeler Formation', 'USA', 39.3, -113.3);
    """)

    conn.commit()
    conn.close()

    # Create overlay DB
    create_overlay_db(overlay_path, canonical_version='1.0.0')

    return db_path, overlay_path


@pytest.fixture
def no_manifest_client(no_manifest_db):
    """Create test client with a plain DB that has no manifest."""
    from starlette.testclient import TestClient
    db_path, overlay_path = no_manifest_db
    scoda_package._set_paths_for_testing(db_path, overlay_path)
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


# ---------------------------------------------------------------------------
# Generic test fixtures (no domain-specific data, no dependencies)
# ---------------------------------------------------------------------------

@pytest.fixture
def generic_db(tmp_path):
    """Create temporary test database with generic sample data.

    No external dependencies — standalone package.
    Tables: categories (hierarchical), items, item_relations, tags.
    """
    canonical_db_path = str(tmp_path / "test_generic.db")
    overlay_db_path = str(tmp_path / "test_generic_overlay.db")

    conn = sqlite3.connect(canonical_db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            description TEXT,
            item_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            FOREIGN KEY (parent_id) REFERENCES categories(id)
        );
        CREATE UNIQUE INDEX idx_categories_uid ON categories(uid);

        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            author TEXT,
            year TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            is_active INTEGER DEFAULT 1,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE UNIQUE INDEX idx_items_uid ON items(uid);

        CREATE TABLE item_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_item_id INTEGER NOT NULL,
            target_item_id INTEGER,
            target_name TEXT,
            relation_type TEXT,
            notes TEXT,
            FOREIGN KEY (source_item_id) REFERENCES items(id),
            FOREIGN KEY (target_item_id) REFERENCES items(id)
        );

        CREATE TABLE tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            tag_name TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items(id)
        );

        -- SCODA Core tables
        CREATE TABLE artifact_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE provenance (
            id INTEGER PRIMARY KEY,
            source_type TEXT NOT NULL,
            citation TEXT NOT NULL,
            description TEXT,
            year INTEGER,
            url TEXT
        );

        CREATE TABLE schema_descriptions (
            table_name TEXT NOT NULL,
            column_name TEXT,
            description TEXT NOT NULL,
            PRIMARY KEY (table_name, column_name)
        );

        CREATE TABLE ui_display_intent (
            id INTEGER PRIMARY KEY,
            entity TEXT NOT NULL,
            default_view TEXT NOT NULL,
            description TEXT,
            source_query TEXT,
            priority INTEGER DEFAULT 0
        );

        CREATE TABLE ui_queries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)

    # Sample data: 3-level category hierarchy + 5 items
    cursor.executescript("""
        -- Categories (root -> group -> subgroup)
        INSERT INTO categories (id, name, level, parent_id, description, item_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Science', 'root', NULL, 'Top-level science category', 5, 'scoda:cat:root:Science', 'name', 'high');
        INSERT INTO categories (id, name, level, parent_id, description, item_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Physics', 'group', 1, 'Physical sciences', 3, 'scoda:cat:group:Physics', 'name', 'high');
        INSERT INTO categories (id, name, level, parent_id, description, item_count, uid, uid_method, uid_confidence)
        VALUES (3, 'Biology', 'group', 1, 'Life sciences', 2, 'scoda:cat:group:Biology', 'name', 'high');
        INSERT INTO categories (id, name, level, parent_id, description, item_count, uid, uid_method, uid_confidence)
        VALUES (4, 'Mechanics', 'subgroup', 2, 'Classical mechanics', 1, 'scoda:cat:subgroup:Mechanics', 'name', 'high');
        INSERT INTO categories (id, name, level, parent_id, description, item_count, uid, uid_method, uid_confidence)
        VALUES (5, 'Ecology', 'subgroup', 3, 'Ecological studies', 1, 'scoda:cat:subgroup:Ecology', 'name', 'high');

        -- Items
        INSERT INTO items (id, name, category_id, author, year, description, status, is_active, uid, uid_method, uid_confidence)
        VALUES (1, 'Gravity', 4, 'Newton', '1687', 'Law of universal gravitation', 'active', 1, 'scoda:item:name:Gravity', 'name', 'high');
        INSERT INTO items (id, name, category_id, author, year, description, status, is_active, uid, uid_method, uid_confidence)
        VALUES (2, 'Relativity', 2, 'Einstein', '1905', 'Special theory of relativity', 'active', 1, 'scoda:item:name:Relativity', 'name', 'high');
        INSERT INTO items (id, name, category_id, author, year, description, status, is_active, uid, uid_method, uid_confidence)
        VALUES (3, 'Evolution', 3, 'Darwin', '1859', 'Theory of evolution by natural selection', 'active', 1, 'scoda:item:name:Evolution', 'name', 'high');
        INSERT INTO items (id, name, category_id, author, year, description, status, is_active, uid, uid_method, uid_confidence)
        VALUES (4, 'Photosynthesis', 5, 'Priestley', '1771', 'Discovery of photosynthesis', 'active', 1, 'scoda:item:name:Photosynthesis', 'name', 'high');
        INSERT INTO items (id, name, category_id, author, year, description, status, is_active, uid, uid_method, uid_confidence)
        VALUES (5, 'Alchemy', 2, 'Unknown', '800', 'Predecessor to modern chemistry', 'deprecated', 0, 'scoda:item:name:Alchemy', 'name', 'medium');

        -- Item relations
        INSERT INTO item_relations (id, source_item_id, target_item_id, target_name, relation_type, notes)
        VALUES (1, 5, 2, 'Relativity', 'superseded_by', 'Modern physics superseded alchemy');

        -- Tags
        INSERT INTO tags (id, item_id, tag_name) VALUES (1, 1, 'classical');
        INSERT INTO tags (id, item_id, tag_name) VALUES (2, 1, 'fundamental');
        INSERT INTO tags (id, item_id, tag_name) VALUES (3, 2, 'modern');
        INSERT INTO tags (id, item_id, tag_name) VALUES (4, 3, 'foundational');
    """)

    # References table (bibliography equivalent, with UIDs)
    cursor.execute("""
        CREATE TABLE "references" (
            id INTEGER PRIMARY KEY,
            authors TEXT NOT NULL,
            year INTEGER,
            title TEXT,
            source TEXT,
            reference_type TEXT DEFAULT 'article',
            raw_entry TEXT NOT NULL,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX idx_references_uid ON "references"(uid)
    """)
    cursor.executescript("""
        INSERT INTO "references" (id, authors, year, title, source, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (1, 'Newton, I.', 1687, 'Principia Mathematica', 'Royal Society', 'article',
                'Newton, I. (1687) Principia Mathematica.',
                'scoda:ref:fp_v1:sha256:test_newton', 'fp_v1', 'medium');
        INSERT INTO "references" (id, authors, year, title, source, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (2, 'Einstein, A.', 1905, 'On the Electrodynamics of Moving Bodies', 'Annalen der Physik', 'article',
                'Einstein, A. (1905) On the Electrodynamics of Moving Bodies.',
                'scoda:ref:doi:10.1234/test-einstein-1905', 'doi', 'high');
        INSERT INTO "references" (id, authors, year, title, source, reference_type, raw_entry,
            uid, uid_method, uid_confidence)
        VALUES (3, 'SEE Darwin.', NULL, NULL, NULL, 'cross_ref',
                'SEE Darwin.',
                'scoda:ref:fp_v1:sha256:test_see_darwin', 'fp_v1', 'low');
    """)

    # SCODA metadata
    cursor.executescript("""
        INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'sample-data');
        INSERT INTO artifact_metadata (key, value) VALUES ('name', 'Sample Data');
        INSERT INTO artifact_metadata (key, value) VALUES ('version', '1.0.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('schema_version', '1.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Generic sample dataset for testing');
        INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');
    """)

    # Provenance
    cursor.executescript("""
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (1, 'primary', 'Test Source (2024)', 'Primary test data source', 2024);
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (2, 'supplementary', 'Additional Source (2025)', 'Supplementary test data', 2025);
    """)

    # Schema descriptions
    cursor.executescript("""
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('categories', NULL, 'Hierarchical category structure');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('categories', 'name', 'Category name');
        INSERT INTO schema_descriptions (table_name, column_name, description)
        VALUES ('items', NULL, 'Collection of data items');
    """)

    # Display intents
    cursor.executescript("""
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (1, 'items', 'tree', 'Category hierarchy is primary structure', 'category_tree', 0);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (2, 'items', 'table', 'Flat listing for search/filtering', 'items_list', 1);
    """)

    # Named queries (11 queries, all local — no cross-DB references)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('items_list', 'Flat list of all items',
                'SELECT id, name, author, year, status, is_active FROM items ORDER BY name',
                NULL, '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('category_items', 'Items in a specific category',
                'SELECT id, name, author, year, is_active FROM items WHERE category_id = :category_id ORDER BY name',
                '{"category_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('category_tree', 'Tree of all categories',
                'SELECT id, name, level, parent_id, description, item_count FROM categories ORDER BY name',
                NULL, '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('item_detail', 'Full detail for a single item',
                'SELECT i.*, c.name as category_name FROM items i LEFT JOIN categories c ON i.category_id = c.id WHERE i.id = :item_id',
                '{"item_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('item_hierarchy', 'Category hierarchy for an item (walk up parent chain)',
                'WITH RECURSIVE ancestors AS (SELECT c.id, c.name, c.level, c.parent_id, 0 as depth FROM categories c WHERE c.id = (SELECT category_id FROM items WHERE id = :item_id) UNION ALL SELECT c.id, c.name, c.level, c.parent_id, a.depth + 1 FROM categories c JOIN ancestors a ON c.id = a.parent_id) SELECT id, name, level FROM ancestors ORDER BY depth DESC',
                '{"item_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('item_relations', 'Relations for a specific item',
                'SELECT r.id, r.target_item_id, COALESCE(t.name, r.target_name) as target_name, r.relation_type, r.notes FROM item_relations r LEFT JOIN items t ON r.target_item_id = t.id WHERE r.source_item_id = :item_id',
                '{"item_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('item_tags', 'Tags for a specific item',
                'SELECT id, tag_name FROM tags WHERE item_id = :item_id ORDER BY tag_name',
                '{"item_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('items_by_category', 'Items in a category (for cross-reference)',
                'SELECT id, name, author, year FROM items WHERE category_id = :category_id ORDER BY name',
                '{"category_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('category_detail', 'Detail for a specific category with parent info',
                'SELECT c.*, p.name as parent_name FROM categories c LEFT JOIN categories p ON c.parent_id = p.id WHERE c.id = :category_id',
                '{"category_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('category_children', 'Direct children of a category',
                'SELECT id, name, level, description, item_count FROM categories WHERE parent_id = :category_id ORDER BY name',
                '{"category_id": "integer"}', '2026-02-20T00:00:00')
    """)
    cursor.execute("""
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('category_children_counts', 'Children counts by level for a category',
                'SELECT level, COUNT(*) as count FROM categories WHERE parent_id = :category_id GROUP BY level',
                '{"category_id": "integer"}', '2026-02-20T00:00:00')
    """)

    # UI Manifest (5 views: 3 tab + 2 detail)
    import json as _json
    generic_manifest = {
        "default_view": "category_tree",
        "views": {
            "category_tree": {
                "type": "hierarchy",
                "display": "tree",
                "title": "Category Tree",
                "description": "Hierarchical category structure",
                "source_query": "category_tree",
                "icon": "bi-diagram-3",
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "sort_by": "label",
                    "order_key": "id"
                },
                "tree_display": {
                    "leaf_rank": "subgroup",
                    "count_key": "item_count",
                    "on_node_info": {"detail_view": "category_detail", "id_key": "id"},
                    "item_query": "category_items",
                    "item_param": "category_id",
                    "item_columns": [
                        {"key": "name", "label": "Item"},
                        {"key": "author", "label": "Author"},
                        {"key": "year", "label": "Year"}
                    ],
                    "on_item_click": {"detail_view": "item_detail", "id_key": "id"},
                    "item_valid_filter": {"key": "is_active", "label": "Active only", "default": True}
                }
            },
            "items_table": {
                "type": "table",
                "title": "All Items",
                "description": "Flat list of all items",
                "source_query": "items_list",
                "icon": "bi-table",
                "columns": [
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "author", "label": "Author", "sortable": True, "searchable": True},
                    {"key": "year", "label": "Year", "sortable": True, "searchable": False},
                    {"key": "status", "label": "Status", "sortable": True, "searchable": True},
                    {"key": "is_active", "label": "Active", "sortable": True, "searchable": False, "type": "boolean"}
                ],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True,
                "on_row_click": {"detail_view": "item_detail", "id_key": "id"}
            },
            "category_radial": {
                "type": "hierarchy",
                "display": "radial",
                "title": "Radial Categories",
                "description": "Category tree in radial layout",
                "source_query": "category_tree",
                "icon": "bi-diagram-2",
                "hierarchy_options": {
                    "id_key": "id",
                    "parent_key": "parent_id",
                    "label_key": "name",
                    "rank_key": "level",
                    "sort_by": "label",
                    "order_key": "id"
                },
                "radial_display": {
                    "leaf_rank": "subgroup",
                    "color_key": "level",
                    "count_key": "item_count",
                    "depth_toggle": True,
                    "rank_radius": {
                        "root": 0.2,
                        "group": 0.5,
                        "subgroup": 1.0
                    },
                    "on_node_click": {"detail_view": "category_detail", "id_field": "id"}
                }
            },
            "item_detail": {
                "type": "detail",
                "title": "Item Detail",
                "source": "/api/composite/item_detail?id={id}",
                "source_query": "item_detail",
                "source_param": "item_id",
                "sub_queries": {
                    "hierarchy": {"query": "item_hierarchy", "params": {"item_id": "id"}},
                    "relations": {"query": "item_relations", "params": {"item_id": "id"}},
                    "tags": {"query": "item_tags", "params": {"item_id": "id"}},
                    "related_items": {"query": "items_by_category", "params": {"category_id": "result.category_id"}}
                },
                "title_template": {"format": "{name}"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [
                         {"key": "name", "label": "Name"},
                         {"key": "category_name", "label": "Category"},
                         {"key": "author", "label": "Author"},
                         {"key": "year", "label": "Year"}
                     ]},
                    {"title": "Relations", "type": "linked_table",
                     "data_key": "relations", "condition": "relations",
                     "columns": [{"key": "target_name", "label": "Target"}],
                     "on_row_click": {"detail_view": "item_detail", "id_key": "target_item_id"}},
                    {"title": "Tags ({count})", "type": "linked_table",
                     "data_key": "tags",
                     "columns": [{"key": "tag_name", "label": "Tag"}]},
                    {"title": "My Notes", "type": "annotations", "entity_type": "item"}
                ]
            },
            "category_detail": {
                "type": "detail",
                "title": "Category Detail",
                "source": "/api/composite/category_detail?id={id}",
                "source_query": "category_detail",
                "source_param": "category_id",
                "sub_queries": {
                    "children_counts": {"query": "category_children_counts", "params": {"category_id": "id"}},
                    "children": {"query": "category_children", "params": {"category_id": "id"}}
                },
                "title_template": {"format": "{name}"},
                "sections": [
                    {"title": "Basic Information", "type": "field_grid",
                     "fields": [
                         {"key": "name", "label": "Name"},
                         {"key": "level", "label": "Level"},
                         {"key": "parent_name", "label": "Parent",
                          "format": "link",
                          "link": {"detail_view": "category_detail", "id_path": "parent_id"}}
                     ]},
                    {"title": "Children", "type": "linked_table",
                     "data_key": "children", "condition": "children",
                     "columns": [{"key": "name", "label": "Name"}]}
                ]
            }
        }
    }
    cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'Test manifest', _json.dumps(generic_manifest), '2026-02-20T00:00:00')
    )

    conn.commit()
    conn.close()

    create_overlay_db(overlay_db_path, canonical_version='1.0.0')
    return canonical_db_path, overlay_db_path


@pytest.fixture
def generic_client(generic_db):
    """Create test client with generic test database (no dependencies)."""
    from starlette.testclient import TestClient
    canonical_db_path, overlay_db_path = generic_db
    scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path)
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


# ---------------------------------------------------------------------------
# Generic dependency DB fixture (replaces paleocore)
# ---------------------------------------------------------------------------

@pytest.fixture
def generic_dep_db(tmp_path):
    """Create a generic dependency database (replaces paleocore).

    Tables: regions, locations, time_periods, time_mapping, entries.
    All tables have UID columns + UNIQUE index + sample data.
    SCODA core tables included (artifact_id='dep-data').
    """
    dep_db_path = str(tmp_path / "test_dep.db")

    conn = sqlite3.connect(dep_db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE regions (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            code TEXT,
            record_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_regions_uid ON regions(uid);

        CREATE TABLE locations (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            code TEXT,
            record_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT,
            FOREIGN KEY (parent_id) REFERENCES locations(id)
        );
        CREATE UNIQUE INDEX idx_locations_uid ON locations(uid);

        CREATE TABLE time_periods (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            name TEXT,
            era TEXT,
            sub_era TEXT,
            start_value REAL,
            end_value REAL,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_time_periods_uid ON time_periods(uid);

        CREATE TABLE time_mapping (
            id INTEGER PRIMARY KEY,
            period_code TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            mapping_type TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (target_id) REFERENCES time_periods(id)
        );
        CREATE INDEX idx_time_mapping_code ON time_mapping(period_code);

        CREATE TABLE entries (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            normalized_name TEXT,
            entry_type TEXT,
            region TEXT,
            period TEXT,
            record_count INTEGER DEFAULT 0,
            uid TEXT,
            uid_method TEXT,
            uid_confidence TEXT,
            same_as_uid TEXT
        );
        CREATE UNIQUE INDEX idx_entries_uid ON entries(uid);
    """)

    # Sample data
    cursor.executescript("""
        INSERT INTO regions (id, name, code, record_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Europe', 'EU', 150, 'scoda:data:region:code:EU', 'code', 'high');
        INSERT INTO regions (id, name, code, record_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Asia', 'AS', 80, 'scoda:data:region:code:AS', 'code', 'high');

        INSERT INTO locations (id, name, level, parent_id, code, record_count, uid, uid_method, uid_confidence)
        VALUES (1, 'Europe', 'region', NULL, 'EU', 150, 'scoda:data:region:code:EU', 'code', 'high');
        INSERT INTO locations (id, name, level, parent_id, code, record_count, uid, uid_method, uid_confidence)
        VALUES (2, 'Asia', 'region', NULL, 'AS', 80, 'scoda:data:region:code:AS', 'code', 'high');
        INSERT INTO locations (id, name, level, parent_id, code, record_count, uid, uid_method, uid_confidence)
        VALUES (3, 'Western Europe', 'subregion', 1, NULL, 50, 'scoda:data:location:name:EU:western_europe', 'name', 'high');
        INSERT INTO locations (id, name, level, parent_id, code, record_count, uid, uid_method, uid_confidence)
        VALUES (4, 'East Asia', 'subregion', 2, NULL, 30, 'scoda:data:location:name:AS:east_asia', 'name', 'high');

        INSERT INTO time_periods (id, code, name, era, sub_era, start_value, end_value, uid, uid_method, uid_confidence)
        VALUES (1, 'ERA-A', 'Era Alpha', 'Ancient', 'Early', 500.0, 400.0, 'scoda:data:period:code:ERA-A', 'code', 'high');
        INSERT INTO time_periods (id, code, name, era, sub_era, start_value, end_value, uid, uid_method, uid_confidence)
        VALUES (2, 'ERA-B', 'Era Beta', 'Middle', 'Late', 400.0, 300.0, 'scoda:data:period:code:ERA-B', 'code', 'high');

        INSERT INTO time_mapping (id, period_code, target_id, mapping_type) VALUES (1, 'ERA-A', 1, 'exact');
        INSERT INTO time_mapping (id, period_code, target_id, mapping_type) VALUES (2, 'ERA-B', 2, 'exact');

        INSERT INTO entries (id, name, normalized_name, entry_type, region, period, record_count,
            uid, uid_method, uid_confidence)
        VALUES (1, 'Alpha Formation', 'alpha formation', 'primary', 'Europe', 'Ancient', 5,
            'scoda:data:entry:fp_v1:sha256:test_alpha', 'fp_v1', 'medium');
        INSERT INTO entries (id, name, normalized_name, entry_type, region, period, record_count,
            uid, uid_method, uid_confidence)
        VALUES (2, 'Beta Site', 'beta site', 'secondary', 'Asia', 'Middle', 20,
            'scoda:data:entry:fp_v1:sha256:test_beta', 'fp_v1', 'medium');
        INSERT INTO entries (id, name, normalized_name, entry_type, region, period, record_count,
            uid, uid_method, uid_confidence)
        VALUES (3, 'Gamma Layer', 'gamma layer', 'primary', 'Europe', 'Ancient', 8,
            'scoda:data:entry:lexicon:ext:12345', 'lexicon', 'high');
    """)

    # SCODA core tables
    cursor.executescript("""
        CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO artifact_metadata (key, value) VALUES ('artifact_id', 'dep-data');
        INSERT INTO artifact_metadata (key, value) VALUES ('name', 'Dep Data');
        INSERT INTO artifact_metadata (key, value) VALUES ('version', '0.3.0');
        INSERT INTO artifact_metadata (key, value) VALUES ('description', 'Generic dependency data');
        INSERT INTO artifact_metadata (key, value) VALUES ('license', 'CC-BY-4.0');

        CREATE TABLE provenance (id INTEGER PRIMARY KEY, source_type TEXT NOT NULL,
            citation TEXT NOT NULL, description TEXT, year INTEGER, url TEXT);
        INSERT INTO provenance (id, source_type, citation, description, year)
        VALUES (1, 'primary', 'Test Dep Source (2024)', 'Dependency test data', 2024);

        CREATE TABLE schema_descriptions (table_name TEXT NOT NULL, column_name TEXT,
            description TEXT NOT NULL, PRIMARY KEY (table_name, column_name));

        CREATE TABLE ui_display_intent (id INTEGER PRIMARY KEY, entity TEXT NOT NULL,
            default_view TEXT NOT NULL, description TEXT, source_query TEXT, priority INTEGER DEFAULT 0);
        INSERT INTO ui_display_intent (id, entity, default_view, description, source_query, priority)
        VALUES (1, 'regions', 'table', 'Region list', 'regions_list', 0);

        CREATE TABLE ui_queries (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
            description TEXT, sql TEXT NOT NULL, params_json TEXT, created_at TEXT NOT NULL);
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('regions_list', 'All regions', 'SELECT id, name FROM regions ORDER BY name', NULL, '2026-02-20T00:00:00');
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('entries_list', 'All entries', 'SELECT id, name FROM entries ORDER BY name', NULL, '2026-02-20T00:00:00');

        CREATE TABLE ui_manifest (name TEXT PRIMARY KEY, description TEXT, manifest_json TEXT NOT NULL, created_at TEXT NOT NULL);
    """)

    import json as _json
    dep_manifest = {
        "default_view": "regions_table",
        "views": {
            "regions_table": {
                "type": "table",
                "title": "Regions",
                "description": "Region data",
                "source_query": "regions_list",
                "icon": "bi-globe",
                "columns": [{"key": "name", "label": "Region", "sortable": True, "searchable": True}],
                "default_sort": {"key": "name", "direction": "asc"},
                "searchable": True
            }
        }
    }
    cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'Dep Data manifest', _json.dumps(dep_manifest), '2026-02-20T00:00:00')
    )

    conn.commit()
    conn.close()

    return dep_db_path


# ---------------------------------------------------------------------------
# Support fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def generic_dep_client(generic_db, generic_dep_db):
    """Create test client with generic DB + generic dependency DB (dep alias)."""
    from starlette.testclient import TestClient
    canonical_db_path, overlay_db_path = generic_db
    dep_path = generic_dep_db
    scoda_package._set_paths_for_testing(canonical_db_path, overlay_db_path, extra_dbs={'dep': dep_path})
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


@pytest.fixture
def generic_mcp_tools_data():
    """Return a test mcp_tools.json dict with 3 tools (single, named_query, composite)."""
    return {
        "format_version": "1.0",
        "tools": [
            {
                "name": "test_search",
                "description": "Test single SQL search",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["pattern"]
                },
                "query_type": "single",
                "sql": "SELECT id, name FROM items WHERE name LIKE :pattern ORDER BY name LIMIT :limit",
                "default_params": {"limit": 10}
            },
            {
                "name": "test_tree",
                "description": "Test named query tree",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "query_type": "named_query",
                "named_query": "category_tree"
            },
            {
                "name": "test_item_detail",
                "description": "Test composite item detail",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "integer"}
                    },
                    "required": ["item_id"]
                },
                "query_type": "composite",
                "view_name": "item_detail",
                "param_mapping": {"item_id": "item_id"}
            }
        ]
    }


@pytest.fixture
def generic_scoda_package(generic_db, tmp_path):
    """Create a .scoda package from generic_db for register_path testing.

    Returns the path to the .scoda file.
    """
    canonical_db_path, overlay_db_path = generic_db
    output_path = str(tmp_path / "sample-data.scoda")
    ScodaPackage.create(canonical_db_path, output_path)
    return output_path


# ---------------------------------------------------------------------------
# CRUD test fixtures — editable_entities manifest
# ---------------------------------------------------------------------------

@pytest.fixture
def crud_db(tmp_path):
    """Create a test DB with editable_entities in the manifest.

    Tables: categories, items (same as generic_db but with editable_entities).
    """
    db_path = str(tmp_path / "test_crud.db")
    overlay_path = str(tmp_path / "test_crud_overlay.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            parent_id INTEGER,
            description TEXT,
            FOREIGN KEY (parent_id) REFERENCES categories(id)
        );

        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            author TEXT,
            year TEXT,
            status TEXT DEFAULT 'active',
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );

        -- Sample data
        INSERT INTO categories (id, name, level, parent_id) VALUES (1, 'Science', 'root', NULL);
        INSERT INTO categories (id, name, level, parent_id) VALUES (2, 'Physics', 'group', 1);
        INSERT INTO categories (id, name, level, parent_id) VALUES (3, 'Biology', 'group', 1);

        INSERT INTO items (id, name, category_id, author, year, status) VALUES (1, 'Gravity', 2, 'Newton', '1687', 'active');
        INSERT INTO items (id, name, category_id, author, year, status) VALUES (2, 'Evolution', 3, 'Darwin', '1859', 'active');
        INSERT INTO items (id, name, category_id, author, year, status) VALUES (3, 'Alchemy', 2, 'Unknown', '800', 'deprecated');

        -- SCODA metadata tables
        CREATE TABLE artifact_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO artifact_metadata VALUES ('name', 'CRUD Test');
        INSERT INTO artifact_metadata VALUES ('version', '1.0.0');
        INSERT INTO artifact_metadata VALUES ('artifact_id', 'crud-test');
        INSERT INTO artifact_metadata VALUES ('description', 'CRUD test database');

        CREATE TABLE provenance (id INTEGER PRIMARY KEY, source_type TEXT, citation TEXT, description TEXT, year INTEGER, url TEXT);
        CREATE TABLE schema_descriptions (table_name TEXT, column_name TEXT, description TEXT, PRIMARY KEY (table_name, column_name));
        CREATE TABLE ui_display_intent (id INTEGER PRIMARY KEY, entity TEXT, default_view TEXT, description TEXT, source_query TEXT, priority INTEGER DEFAULT 0);

        CREATE TABLE ui_queries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            sql TEXT NOT NULL,
            params_json TEXT,
            created_at TEXT NOT NULL
        );

        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('items_list', 'All items', 'SELECT id, name, author, year, status FROM items ORDER BY name', NULL, '2026-01-01');
        INSERT INTO ui_queries (name, description, sql, params_json, created_at)
        VALUES ('categories_list', 'All categories', 'SELECT id, name, level FROM categories ORDER BY name', NULL, '2026-01-01');

        CREATE TABLE ui_manifest (
            name TEXT PRIMARY KEY,
            description TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
    """)

    manifest = {
        "default_view": "items_table",
        "views": {
            "items_table": {
                "type": "table",
                "title": "Items",
                "source_query": "items_list",
                "columns": [
                    {"key": "name", "label": "Name", "sortable": True, "searchable": True},
                    {"key": "author", "label": "Author", "sortable": True},
                    {"key": "year", "label": "Year", "sortable": True},
                    {"key": "status", "label": "Status", "sortable": True},
                ],
                "default_sort": {"key": "name", "direction": "asc"},
            },
        },
        "editable_entities": {
            "item": {
                "table": "items",
                "pk": "id",
                "operations": ["create", "read", "update", "delete"],
                "fields": {
                    "name": {"type": "text", "required": True, "label": "Name"},
                    "category_id": {"type": "integer", "fk": "categories.id", "label": "Category"},
                    "author": {"type": "text", "label": "Author"},
                    "year": {"type": "text", "label": "Year"},
                    "status": {"type": "text", "enum": ["active", "deprecated", "draft"], "default": "active", "label": "Status"},
                    "is_active": {"type": "boolean", "default": 1, "label": "Active"},
                },
                "constraints": [
                    {"type": "unique_where", "where": "1=1", "fields": ["name"], "message": "Duplicate item name"}
                ],
            },
            "category": {
                "table": "categories",
                "pk": "id",
                "operations": ["create", "read", "update"],
                "fields": {
                    "name": {"type": "text", "required": True, "label": "Name"},
                    "level": {"type": "text", "required": True, "enum": ["root", "group", "subgroup"], "label": "Level"},
                    "parent_id": {"type": "integer", "fk": "categories.id", "label": "Parent"},
                    "description": {"type": "text", "label": "Description"},
                },
            },
        },
    }

    cursor.execute(
        "INSERT INTO ui_manifest (name, description, manifest_json, created_at) VALUES (?, ?, ?, ?)",
        ('default', 'CRUD test manifest', json.dumps(manifest), '2026-01-01')
    )

    conn.commit()
    conn.close()

    create_overlay_db(overlay_path, canonical_version='1.0.0')
    return db_path, overlay_path


@pytest.fixture
def crud_client(crud_db):
    """Test client wired to crud_db in admin mode."""
    from starlette.testclient import TestClient
    from scoda_engine.app import _set_scoda_mode
    db_path, overlay_path = crud_db
    scoda_package._set_paths_for_testing(db_path, overlay_path)
    _set_scoda_mode('admin')
    with TestClient(app) as client:
        yield client
    _set_scoda_mode('viewer')
    scoda_package._reset_paths()


@pytest.fixture
def crud_viewer_client(crud_db):
    """Test client wired to crud_db in viewer mode (read-only)."""
    from starlette.testclient import TestClient
    from scoda_engine.app import _set_scoda_mode
    db_path, overlay_path = crud_db
    scoda_package._set_paths_for_testing(db_path, overlay_path)
    _set_scoda_mode('viewer')
    with TestClient(app) as client:
        yield client
    scoda_package._reset_paths()


@pytest.fixture
def generic_scoda_with_mcp_tools(generic_db, generic_mcp_tools_data, tmp_path):
    """Create a .scoda package that includes mcp_tools.json (generic version)."""
    canonical_db_path, overlay_db_path = generic_db

    # Write mcp_tools.json to a temp file
    mcp_tools_path = str(tmp_path / "mcp_tools.json")
    with open(mcp_tools_path, 'w') as f:
        json.dump(generic_mcp_tools_data, f)

    # Create .scoda package
    output_path = str(tmp_path / "test_with_mcp.scoda")
    ScodaPackage.create(
        canonical_db_path,
        output_path,
        mcp_tools_path=mcp_tools_path
    )

    return output_path, canonical_db_path, overlay_db_path
