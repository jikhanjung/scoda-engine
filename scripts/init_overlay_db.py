#!/usr/bin/env python3
"""
Initialize overlay database for user annotations.

Creates a separate SQLite database for user-editable content,
keeping canonical data immutable.
"""

import sqlite3
import os
import sys


def create_overlay_db(db_path, canonical_version='1.0.0'):
    """
    Create overlay database with metadata and user_annotations table.

    Args:
        db_path: Path to overlay database file
        canonical_version: Version of canonical database (from artifact_metadata)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # overlay_metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overlay_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Store canonical DB version for migration tracking
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('canonical_version', ?)",
        (canonical_version,)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('created_at', datetime('now'))"
    )

    # user_annotations table (from Phase 17, now in overlay)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            entity_name TEXT,
            annotation_type TEXT NOT NULL,
            content TEXT NOT NULL,
            author TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_annotations_entity
            ON user_annotations(entity_type, entity_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_annotations_name
            ON user_annotations(entity_name)
    """)

    conn.commit()
    conn.close()


def main():
    """Command-line interface for creating overlay DB."""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = 'trilobase_overlay.db'

    canonical_version = sys.argv[2] if len(sys.argv) > 2 else '1.0.0'

    if os.path.exists(db_path):
        print(f"Warning: {db_path} already exists. Skipping creation.")
        return

    create_overlay_db(db_path, canonical_version)
    print(f"✓ Overlay DB created: {db_path}")
    print(f"  Canonical version: {canonical_version}")

    # Verify
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"  Tables: {', '.join(tables)}")


if __name__ == '__main__':
    main()
