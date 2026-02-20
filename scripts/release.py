#!/usr/bin/env python3
"""
SCODA Release Mechanism

Packages a versioned, self-contained release artifact:
  releases/{artifact_id}-v{version}/
  ├── {artifact_id}.db     (read-only SQLite copy)
  ├── metadata.json        (identity + provenance + statistics)
  ├── checksums.sha256     (sha256sum --check compatible)
  └── README.md            (usage notes)

Usage:
  python scripts/release.py              # create release
  python scripts/release.py --dry-run    # preview without side-effects
"""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import sys
from datetime import datetime, timezone

# Add parent directory for scoda_package import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from scoda_engine.scoda_package import ScodaPackage

# SCODA core tables excluded from auto-discovery statistics
_SCODA_META_TABLES = {
    'artifact_metadata', 'provenance', 'schema_descriptions',
    'ui_display_intent', 'ui_queries', 'ui_manifest',
}

DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), '..', 'releases')


def get_version(db_path):
    """Read version from artifact_metadata table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM artifact_metadata WHERE key = 'version'")
    row = cursor.fetchone()
    conn.close()
    if not row:
        print("Error: No 'version' key in artifact_metadata.", file=sys.stderr)
        raise SystemExit(1)
    return row['value']


def get_artifact_id(db_path):
    """Read artifact_id from artifact_metadata table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM artifact_metadata WHERE key = 'artifact_id'")
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else 'unknown'


def get_artifact_name(db_path):
    """Read name from artifact_metadata table."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT value FROM artifact_metadata WHERE key = 'name'")
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else 'Unknown'


def calculate_sha256(file_path):
    """Calculate SHA-256 hash of a file using 8KB chunks."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def store_sha256(db_path, sha256_hash):
    """Store sha256 hash in the source DB's artifact_metadata."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO artifact_metadata (key, value) VALUES ('sha256', ?)",
        (sha256_hash,))
    conn.commit()
    conn.close()


def get_statistics(db_path):
    """Calculate database statistics by auto-discovering user tables."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Discover all user tables (exclude SCODA meta tables and sqlite internals)
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    all_tables = [row['name'] for row in cursor.fetchall()]

    stats = {}
    total = 0
    for table in sorted(all_tables):
        if table in _SCODA_META_TABLES:
            continue
        cursor.execute(f"SELECT COUNT(*) as count FROM [{table}]")
        count = cursor.fetchone()['count']
        stats[table] = count
        total += count

    stats['total_records'] = total
    conn.close()
    return stats


def get_provenance(db_path):
    """Return provenance records as a list of dicts."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM provenance ORDER BY id")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def build_metadata_json(db_path, sha256_hash):
    """Build the metadata.json content as a dict."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM artifact_metadata")
    metadata = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()

    stats = get_statistics(db_path)
    provenance = get_provenance(db_path)

    result = {
        'artifact_id': metadata.get('artifact_id', 'unknown'),
        'name': metadata.get('name', 'Unknown'),
        'version': metadata.get('version'),
        'schema_version': metadata.get('schema_version', '1.0'),
        'created_at': metadata.get('created_at',
                                   datetime.now(timezone.utc).strftime('%Y-%m-%d')),
        'description': metadata.get('description', ''),
        'license': metadata.get('license', ''),
        'released_at': datetime.now(timezone.utc).isoformat(),
        'sha256': sha256_hash,
        'provenance': provenance,
        'statistics': stats,
    }
    return result


def generate_readme(version, sha256_hash, stats, artifact_id=None, name=None):
    """Generate a release README.md string."""
    artifact_id = artifact_id or 'unknown'
    name = name or 'Unknown'
    db_filename = f"{artifact_id}.db"

    lines = [
        f"# {name} v{version}",
        "",
        "SCODA data artifact.",
        "",
        "## Contents",
        "",
        "| File | Description |",
        "|------|-------------|",
        f"| `{db_filename}` | SQLite database (read-only) |",
        "| `metadata.json` | Artifact metadata, provenance, and statistics |",
        "| `checksums.sha256` | SHA-256 checksum for integrity verification |",
        "| `README.md` | This file |",
        "",
        "## Verification",
        "",
        "```bash",
        "sha256sum --check checksums.sha256",
        "```",
        "",
        f"Expected SHA-256: `{sha256_hash}`",
        "",
        "## Statistics",
        "",
    ]

    for key, value in stats.items():
        lines.append(f"- {key}: {value}")

    lines += [
        "",
        "## Usage",
        "",
        "```bash",
        f"sqlite3 {db_filename}",
        "```",
        "",
        "```sql",
        "-- Browse metadata",
        "SELECT * FROM artifact_metadata;",
        "```",
        "",
        "## License",
        "",
        "See metadata.json for license information.",
        "",
    ]
    return "\n".join(lines)


def create_release(db_path, output_dir):
    """Main orchestration: create a release package."""
    # 1. Validate
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        raise SystemExit(1)

    version = get_version(db_path)
    artifact_id = get_artifact_id(db_path)
    name = get_artifact_name(db_path)
    db_filename = f"{artifact_id}.db"
    scoda_filename = f"{artifact_id}.scoda"

    # 2. Determine release directory
    release_dir = os.path.join(
        os.path.abspath(output_dir), f"{artifact_id}-v{version}")

    # 3. Refuse to overwrite (immutability)
    if os.path.exists(release_dir):
        print(
            f"Error: Release directory already exists: {release_dir}",
            file=sys.stderr)
        print("SCODA immutability principle: cannot overwrite an existing release.",
              file=sys.stderr)
        raise SystemExit(1)

    os.makedirs(release_dir)

    # 4. Copy DB
    db_dest = os.path.join(release_dir, db_filename)
    shutil.copy2(db_path, db_dest)

    # 5. Set read-only
    os.chmod(db_dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)  # 444

    # 6. Calculate SHA-256 of the release copy
    sha256_hash = calculate_sha256(db_dest)

    # 7. Store sha256 in the source DB
    store_sha256(db_path, sha256_hash)

    # 8. Build and write metadata.json
    metadata = build_metadata_json(db_path, sha256_hash)
    metadata_path = os.path.join(release_dir, 'metadata.json')
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 9. Write checksums.sha256
    checksums_path = os.path.join(release_dir, 'checksums.sha256')
    with open(checksums_path, 'w', encoding='utf-8') as f:
        f.write(f"{sha256_hash}  {db_filename}\n")

    # 10. Generate README.md
    stats = get_statistics(db_path)
    readme_content = generate_readme(version, sha256_hash, stats,
                                     artifact_id=artifact_id, name=name)
    readme_path = os.path.join(release_dir, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    # 11. Create .scoda package in release directory
    scoda_dest = os.path.join(release_dir, scoda_filename)
    ScodaPackage.create(db_path, scoda_dest)

    # 12. Summary
    print(f"Release created: {release_dir}")
    print(f"  Version:  {version}")
    print(f"  SHA-256:  {sha256_hash}")
    print(f"  Files:")
    for fname in [db_filename, scoda_filename, 'metadata.json', 'checksums.sha256', 'README.md']:
        fpath = os.path.join(release_dir, fname)
        size = os.path.getsize(fpath)
        print(f"    {fname:20s} {size:>10,} bytes")
    print()
    print("To tag this release in git:")
    print(f"  git tag -a v{version} -m 'Release v{version}'")
    print(f"  git push origin v{version}")

    return release_dir


def main():
    parser = argparse.ArgumentParser(
        description='Create a SCODA release package')
    parser.add_argument(
        '--db',
        help='Path to source SQLite database')
    parser.add_argument(
        '--output-dir', default=DEFAULT_OUTPUT,
        help='Output directory for releases (default: releases/)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Preview release without creating files')
    args = parser.parse_args()

    db_path = os.path.abspath(args.db) if args.db else None
    output_dir = os.path.abspath(args.output_dir)

    if not db_path or not os.path.exists(db_path):
        print(f"Error: Database not found: {db_path}", file=sys.stderr)
        raise SystemExit(1)

    version = get_version(db_path)
    artifact_id = get_artifact_id(db_path)
    release_dir = os.path.join(output_dir, f"{artifact_id}-v{version}")

    if args.dry_run:
        db_filename = f"{artifact_id}.db"
        print("=== DRY RUN (no files will be created) ===")
        print()
        print(f"Source DB:     {db_path}")
        print(f"Artifact ID:   {artifact_id}")
        print(f"Version:       {version}")
        print(f"Release dir:   {release_dir}")
        print()

        if os.path.exists(release_dir):
            print(f"WARNING: Release directory already exists — "
                  f"actual run would fail.")
        else:
            print("Release directory does not exist — OK to proceed.")

        print()
        print("Files that would be created:")
        print(f"  {release_dir}/{db_filename}        (read-only copy)")
        print(f"  {release_dir}/metadata.json       (metadata + provenance)")
        print(f"  {release_dir}/checksums.sha256    (SHA-256 hash)")
        print(f"  {release_dir}/README.md           (usage notes)")
        print()

        stats = get_statistics(db_path)
        print("Database statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        return

    create_release(db_path, output_dir)


if __name__ == '__main__':
    main()
