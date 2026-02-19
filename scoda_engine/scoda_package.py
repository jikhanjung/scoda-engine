"""
scoda_package.py — .scoda ZIP package support and centralized DB access

This module provides:
  A. ScodaPackage class: open/create .scoda ZIP archives
  B. PackageRegistry class: discover and manage multiple .scoda packages
  C. Centralized DB access functions (replaces duplicated logic in app.py, mcp_server.py, gui.py, serve.py)

.scoda format:
  example.scoda (ZIP archive)
  ├── manifest.json   # package metadata
  ├── data.db         # SQLite database
  └── assets/         # future images/documents (currently empty)
"""

import atexit
import glob as glob_mod
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
import tempfile
import zipfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# A. ScodaPackage class
# ---------------------------------------------------------------------------

class ScodaPackage:
    """Read/write .scoda ZIP-based data packages."""

    def __init__(self, scoda_path):
        """Open an existing .scoda package.

        Extracts data.db to a temp file for SQLite access.
        Temp file is cleaned up on close() or at process exit.
        """
        self.scoda_path = os.path.abspath(scoda_path)
        if not os.path.exists(self.scoda_path):
            raise FileNotFoundError(f".scoda file not found: {self.scoda_path}")

        logger.info("Opening .scoda package: %s", os.path.basename(self.scoda_path))
        self._tmp_dir = tempfile.mkdtemp(prefix="scoda_")
        self._zf = zipfile.ZipFile(self.scoda_path, 'r')

        # Read manifest
        try:
            self.manifest = json.loads(self._zf.read('manifest.json'))
        except KeyError:
            self.close()
            raise ValueError("Invalid .scoda package: missing manifest.json")

        logger.debug("Manifest: name=%s version=%s records=%s",
                      self.manifest.get('name'), self.manifest.get('version'),
                      self.manifest.get('record_count'))

        # Extract data.db to temp directory
        data_file = self.manifest.get('data_file', 'data.db')
        try:
            self._zf.extract(data_file, self._tmp_dir)
        except KeyError:
            self.close()
            raise ValueError(f"Invalid .scoda package: missing {data_file}")

        self.db_path = os.path.join(self._tmp_dir, data_file)

        # Register cleanup
        atexit.register(self.close)

    @property
    def version(self):
        return self.manifest.get('version', 'unknown')

    @property
    def name(self):
        return self.manifest.get('name', 'unknown')

    @property
    def title(self):
        return self.manifest.get('title', self.name)

    @property
    def record_count(self):
        return self.manifest.get('record_count', 0)

    @property
    def data_checksum(self):
        return self.manifest.get('data_checksum_sha256', '')

    def verify_checksum(self):
        """Verify data.db SHA-256 matches manifest."""
        if not self.data_checksum:
            return True  # no checksum in manifest, skip
        actual = _sha256_file(self.db_path)
        return actual == self.data_checksum

    def get_asset(self, asset_path):
        """Read a file from the assets/ directory inside the package."""
        full_path = f"assets/{asset_path}"
        try:
            return self._zf.read(full_path)
        except KeyError:
            return None

    def list_assets(self):
        """List files in the assets/ directory."""
        return [n for n in self._zf.namelist()
                if n.startswith('assets/') and not n.endswith('/')]

    @property
    def mcp_tools(self):
        """Read mcp_tools.json from the package. Returns parsed dict or None."""
        try:
            data = self._zf.read('mcp_tools.json')
            return json.loads(data)
        except KeyError:
            return None

    @property
    def has_reference_spa(self):
        """Check if this package contains a Reference SPA."""
        return self.manifest.get('has_reference_spa', False)

    def close(self):
        """Clean up temp files."""
        if hasattr(self, '_zf') and self._zf:
            try:
                self._zf.close()
            except Exception:
                pass
            self._zf = None

        if hasattr(self, '_tmp_dir') and self._tmp_dir and os.path.exists(self._tmp_dir):
            try:
                shutil.rmtree(self._tmp_dir)
            except Exception:
                pass
            self._tmp_dir = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def create(db_path, output_path, metadata=None, extra_assets=None, mcp_tools_path=None):
        """Create a .scoda package from a SQLite database.

        Args:
            db_path: Path to the source SQLite database.
            output_path: Path for the output .scoda file.
            metadata: Optional dict to override/extend manifest fields.
            extra_assets: Optional dict of {archive_path: local_path} for additional files.
            mcp_tools_path: Optional path to mcp_tools.json to include in the package.

        Returns:
            Path to the created .scoda file.
        """
        db_path = os.path.abspath(db_path)
        output_path = os.path.abspath(output_path)

        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")

        # Read metadata from DB
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT key, value FROM artifact_metadata")
        db_meta = {row['key']: row['value'] for row in cursor.fetchall()}

        # Count records: sum all non-SCODA-metadata tables
        scoda_meta_tables = {'artifact_metadata', 'provenance', 'schema_descriptions',
                             'ui_display_intent', 'ui_queries', 'ui_manifest'}
        all_tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        record_count = 0
        for (table_name,) in all_tables:
            if table_name not in scoda_meta_tables and not table_name.startswith('sqlite_'):
                cnt = cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]").fetchone()[0]
                record_count += cnt

        conn.close()

        # Calculate checksum
        checksum = _sha256_file(db_path)

        # Build manifest
        manifest = {
            "format": "scoda",
            "format_version": "1.0",
            "name": db_meta.get('artifact_id', 'unknown'),
            "version": db_meta.get('version', '1.0.0'),
            "title": db_meta.get('name', 'Unknown') + ' - ' + db_meta.get('description', ''),
            "description": db_meta.get('description', ''),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "license": db_meta.get('license', 'CC-BY-4.0'),
            "authors": [],
            "data_file": "data.db",
            "record_count": record_count,
            "data_checksum_sha256": checksum,
        }

        # Override with user-supplied metadata
        if metadata:
            manifest.update(metadata)

        # Create ZIP
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
            zf.write(db_path, 'data.db')
            # Create empty assets/ directory entry
            zf.writestr('assets/', '')
            # Add MCP tools definition
            if mcp_tools_path and os.path.exists(mcp_tools_path):
                zf.write(mcp_tools_path, 'mcp_tools.json')
            # Add extra assets (e.g., Reference SPA files)
            if extra_assets:
                for archive_path, local_path in extra_assets.items():
                    zf.write(local_path, archive_path)

        return output_path


# ---------------------------------------------------------------------------
# B. PackageRegistry — discover and manage multiple .scoda packages
# ---------------------------------------------------------------------------

class PackageRegistry:
    """Discover and manage multiple .scoda packages."""

    def __init__(self):
        self._packages = {}   # name → {pkg: ScodaPackage, db_path, overlay_path, deps: [...]}
        self._scan_dir = None

    def scan(self, directory):
        """Scan directory for *.scoda files and register each package."""
        directory = os.path.abspath(directory)
        self._scan_dir = directory
        logger.info("Scanning for packages in: %s", directory)

        # Find .scoda files
        scoda_files = sorted(glob_mod.glob(os.path.join(directory, '*.scoda')))

        for scoda_path in scoda_files:
            try:
                pkg = ScodaPackage(scoda_path)
                name = pkg.name
                overlay_path = os.path.join(directory, f'{name}_overlay.db')
                deps = pkg.manifest.get('dependencies', [])
                self._packages[name] = {
                    'pkg': pkg,
                    'db_path': pkg.db_path,
                    'overlay_path': overlay_path,
                    'deps': deps,
                }
            except (ValueError, FileNotFoundError) as e:
                logger.warning("Skipping invalid package %s: %s",
                               os.path.basename(scoda_path), e)
                continue  # skip invalid packages

        # Fallback: if no .scoda found, look for *.db files
        if not self._packages:
            for db_path in sorted(glob_mod.glob(os.path.join(directory, '*.db'))):
                db_name = os.path.basename(db_path)
                # Skip overlay DBs
                if db_name.endswith('_overlay.db'):
                    continue
                name = os.path.splitext(db_name)[0]
                overlay_path = os.path.join(directory, f'{name}_overlay.db')
                self._packages[name] = {
                    'pkg': None,
                    'db_path': db_path,
                    'overlay_path': overlay_path,
                    'deps': [],
                }

    def get_db(self, name):
        """Get DB connection for a specific package with dependencies ATTACHed.

        Args:
            name: Package name

        Returns:
            sqlite3.Connection with row_factory=sqlite3.Row

        Raises:
            KeyError: If package not found
        """
        if name not in self._packages:
            raise KeyError(f'Package not found: {name}')

        entry = self._packages[name]
        db_path = entry['db_path']
        overlay_path = entry['overlay_path']

        # Ensure overlay DB exists
        _ensure_overlay_for_package(db_path, overlay_path)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(f"ATTACH DATABASE '{overlay_path}' AS overlay")
        logger.debug("get_db(%s): attached overlay", name)

        # Attach dependencies
        for dep in entry['deps']:
            dep_name = dep.get('name')
            alias = dep.get('alias', dep_name)
            if dep_name in self._packages:
                dep_db_path = self._packages[dep_name]['db_path']
                conn.execute(f"ATTACH DATABASE '{dep_db_path}' AS {alias}")
                logger.debug("get_db(%s): attached dependency %s as %s",
                             name, dep_name, alias)

        return conn

    def list_packages(self):
        """Return list of discovered package info dicts."""
        result = []
        for name, entry in self._packages.items():
            pkg = entry['pkg']
            info = {
                'name': name,
                'title': pkg.title if pkg else name,
                'version': pkg.version if pkg else 'unknown',
                'record_count': pkg.record_count if pkg else 0,
                'description': pkg.manifest.get('description', '') if pkg else '',
                'has_dependencies': len(entry['deps']) > 0,
                'source_type': 'scoda' if pkg else 'db',
                'deps': entry['deps'],
            }
            result.append(info)
        return result

    def get_package(self, name):
        """Return package entry or raise KeyError."""
        if name not in self._packages:
            raise KeyError(f'Package not found: {name}')
        entry = self._packages[name]
        pkg = entry['pkg']
        return {
            'name': name,
            'title': pkg.title if pkg else name,
            'version': pkg.version if pkg else 'unknown',
            'record_count': pkg.record_count if pkg else 0,
            'description': pkg.manifest.get('description', '') if pkg else '',
            'has_dependencies': len(entry['deps']) > 0,
            'source_type': 'scoda' if pkg else 'db',
            'db_path': entry['db_path'],
            'overlay_path': entry['overlay_path'],
            'deps': entry['deps'],
            'manifest': pkg.manifest if pkg else None,
        }

    def get_mcp_tools(self, name):
        """Return mcp_tools.json content for a specific package, or None."""
        if name not in self._packages:
            return None
        pkg = self._packages[name].get('pkg')
        if pkg:
            return pkg.mcp_tools
        return None

    def close_all(self):
        """Close all ScodaPackage instances."""
        for entry in self._packages.values():
            if entry['pkg']:
                entry['pkg'].close()
        self._packages.clear()


def _ensure_overlay_for_package(canonical_db_path, overlay_path):
    """Create overlay DB for a package if it doesn't exist."""
    if os.path.exists(overlay_path):
        return
    logger.info("Creating overlay DB: %s", os.path.basename(overlay_path))

    # Get canonical version
    try:
        conn = sqlite3.connect(canonical_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
        row = cursor.fetchone()
        version = row[0] if row else '1.0.0'
        conn.close()
    except Exception:
        version = '1.0.0'

    conn = sqlite3.connect(overlay_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overlay_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('canonical_version', ?)",
        (version,)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('created_at', datetime('now'))"
    )
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


# Module-level default registry (lazy-initialized)
_registry = None


def get_registry():
    """Get the default PackageRegistry (lazy-initialized)."""
    global _registry
    if _registry is None:
        _registry = PackageRegistry()
        if getattr(sys, 'frozen', False):
            scan_dir = os.path.dirname(sys.executable)
        else:
            scan_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _registry.scan(scan_dir)
    return _registry


def get_mcp_tools():
    """Get mcp_tools for the active package (or None)."""
    name = get_active_package_name()
    if name:
        return get_registry().get_mcp_tools(name)
    # Legacy mode: check if the module-level _scoda_pkg has mcp_tools
    _resolve_paths()
    if _scoda_pkg:
        return _scoda_pkg.mcp_tools
    return None


def _reset_registry():
    """Reset the default registry (for testing teardown)."""
    global _registry
    if _registry:
        _registry.close_all()
    _registry = None


# ---------------------------------------------------------------------------
# C. Centralized DB access (replaces duplicated logic in 4 files)
# ---------------------------------------------------------------------------

# Module-level paths — resolved once at import time, overridable for testing
_canonical_db = None
_overlay_db = None
_dep_dbs = {}  # {alias: path} — dependency databases to ATTACH
_scoda_pkg = None  # ScodaPackage instance (if using .scoda)
_dep_pkgs = []  # ScodaPackage instances for dependencies (to close on reset)
_active_package_name = None  # GUI/CLI selected package (routes get_db through registry)


def set_active_package(name):
    """Set the active package. GUI/CLI calls this so get_db() uses the registry."""
    global _active_package_name
    _active_package_name = name


def get_active_package_name():
    """Return the currently active package name (or None)."""
    return _active_package_name


def _resolve_dependencies(base_dir):
    """Resolve dependency databases from main package manifest.

    First checks the .scoda manifest for declared dependencies.
    Then, if no 'pc' dependency was found, tries to discover
    paleocore.scoda or paleocore.db alongside the main package
    (covers .db fallback mode and stale .scoda builds).
    """
    global _dep_dbs, _dep_pkgs

    if _scoda_pkg:
        deps = _scoda_pkg.manifest.get('dependencies', [])
        for dep in deps:
            dep_name = dep.get('name')
            alias = dep.get('alias', dep_name)
            if not dep_name:
                continue
            # Try .scoda first, then .db
            dep_scoda = os.path.join(base_dir, f'{dep_name}.scoda')
            if os.path.exists(dep_scoda):
                pkg = ScodaPackage(dep_scoda)
                _dep_pkgs.append(pkg)
                _dep_dbs[alias] = pkg.db_path
            else:
                dep_db = os.path.join(base_dir, f'{dep_name}.db')
                if os.path.exists(dep_db):
                    _dep_dbs[alias] = dep_db

    # Fallback: auto-discover paleocore if 'pc' alias not yet resolved
    if 'pc' not in _dep_dbs:
        for candidate in ('paleocore.scoda', 'paleocore.db'):
            candidate_path = os.path.join(base_dir, candidate)
            if os.path.exists(candidate_path):
                if candidate.endswith('.scoda'):
                    pkg = ScodaPackage(candidate_path)
                    _dep_pkgs.append(pkg)
                    _dep_dbs['pc'] = pkg.db_path
                else:
                    _dep_dbs['pc'] = candidate_path
                logger.info("Auto-discovered dependency: pc=%s", candidate)
                break


def _resolve_paths():
    """Resolve canonical DB, overlay DB, and dependency DB paths.

    Priority:
      1. If _set_paths_for_testing() was called, use those paths.
      2. Frozen mode (PyInstaller): look for .scoda next to executable, fallback to bundled .db.
      3. Dev mode: look for .scoda in project root, fallback to .db.
    """
    global _canonical_db, _overlay_db, _scoda_pkg

    if _canonical_db is not None:
        return  # already resolved (or set by testing)

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        logger.debug("Frozen mode, base_dir=%s", base_dir)
    else:
        # Development mode — project root is one level up from this package
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logger.debug("Dev mode, base_dir=%s", base_dir)

    # Find first .scoda file
    scoda_files = sorted(glob_mod.glob(os.path.join(base_dir, '*.scoda')))
    if scoda_files:
        scoda_path = scoda_files[0]
        _scoda_pkg = ScodaPackage(scoda_path)
        _canonical_db = _scoda_pkg.db_path
        name = os.path.splitext(os.path.basename(scoda_path))[0]
        _overlay_db = os.path.join(base_dir, f'{name}_overlay.db')
    else:
        # Fallback: find first .db file
        db_files = sorted(glob_mod.glob(os.path.join(base_dir, '*.db')))
        db_files = [f for f in db_files if not f.endswith('_overlay.db')]
        if db_files:
            _canonical_db = db_files[0]
            name = os.path.splitext(os.path.basename(db_files[0]))[0]
            _overlay_db = os.path.join(base_dir, f'{name}_overlay.db')
            logger.debug("Fallback to .db file: %s", os.path.basename(_canonical_db))
        elif getattr(sys, 'frozen', False):
            # Last resort: bundled DB inside PyInstaller bundle
            _canonical_db = os.path.join(sys._MEIPASS, 'data.db')
            _overlay_db = os.path.join(base_dir, 'data_overlay.db')
        else:
            _canonical_db = os.path.join(base_dir, 'data.db')
            _overlay_db = os.path.join(base_dir, 'data_overlay.db')

    logger.info("Resolved DB: canonical=%s, overlay=%s",
                os.path.basename(_canonical_db), os.path.basename(_overlay_db))
    _resolve_dependencies(base_dir)


def _set_paths_for_testing(canonical_path, overlay_path, extra_dbs=None):
    """Override DB paths for testing. Call before any get_db().

    Args:
        canonical_path: Path to the main database.
        overlay_path: Path to the overlay database.
        extra_dbs: Optional dict of {alias: path} for dependency databases.
    """
    global _canonical_db, _overlay_db, _dep_dbs, _scoda_pkg, _dep_pkgs, _active_package_name
    _active_package_name = None  # tests use direct paths, not registry
    _canonical_db = canonical_path
    _overlay_db = overlay_path
    _dep_dbs = extra_dbs or {}
    _scoda_pkg = None
    _dep_pkgs = []


def _reset_paths():
    """Reset resolved paths (for testing teardown)."""
    global _canonical_db, _overlay_db, _dep_dbs, _scoda_pkg, _dep_pkgs, _active_package_name
    if _scoda_pkg:
        _scoda_pkg.close()
    for pkg in _dep_pkgs:
        pkg.close()
    _canonical_db = None
    _overlay_db = None
    _dep_dbs = {}
    _scoda_pkg = None
    _dep_pkgs = []
    _active_package_name = None


def get_canonical_db_path():
    """Return the resolved canonical DB path."""
    _resolve_paths()
    return _canonical_db


def get_overlay_db_path():
    """Return the resolved overlay DB path."""
    _resolve_paths()
    return _overlay_db


def ensure_overlay_db():
    """Create overlay DB if it doesn't exist."""
    _resolve_paths()

    if os.path.exists(_overlay_db):
        return
    logger.info("Creating overlay DB: %s", os.path.basename(_overlay_db))

    # Get canonical version
    try:
        conn = sqlite3.connect(_canonical_db)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM artifact_metadata WHERE key = 'version'")
        row = cursor.fetchone()
        version = row[0] if row else '1.0.0'
        conn.close()
    except Exception:
        version = '1.0.0'

    # Create overlay DB
    conn = sqlite3.connect(_overlay_db)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS overlay_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('canonical_version', ?)",
        (version,)
    )
    cursor.execute(
        "INSERT OR REPLACE INTO overlay_metadata (key, value) VALUES ('created_at', datetime('now'))"
    )

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


def get_db():
    """Get database connection with overlay and dependencies attached.

    Returns a sqlite3.Connection with row_factory=sqlite3.Row.

    When _active_package_name is set (by GUI/CLI), the connection is obtained
    from the PackageRegistry instead of the legacy path resolution.

    Attached databases:
      - overlay: user annotations (read/write)
      - Dependencies defined in manifest (read-only, optional)
    """
    # Active package mode (GUI/CLI selected a package)
    if _active_package_name is not None:
        return get_registry().get_db(_active_package_name)

    # Legacy mode (direct path resolution)
    _resolve_paths()
    ensure_overlay_db()

    conn = sqlite3.connect(_canonical_db)
    conn.row_factory = sqlite3.Row
    conn.execute(f"ATTACH DATABASE '{_overlay_db}' AS overlay")

    # Attach dependency databases
    for alias, dep_path in _dep_dbs.items():
        if os.path.exists(dep_path):
            conn.execute(f"ATTACH DATABASE '{dep_path}' AS {alias}")

    return conn


def get_scoda_info():
    """Return package info dict for GUI display.

    Returns:
        dict with keys: source_type ('scoda' or 'db'), canonical_path, overlay_path,
              dep_dbs, and optionally: version, name, record_count, checksum.
    """
    _resolve_paths()

    info = {
        'canonical_path': _canonical_db,
        'overlay_path': _overlay_db,
        'dep_dbs': dict(_dep_dbs),
        'canonical_exists': os.path.exists(_canonical_db),
        'overlay_exists': os.path.exists(_overlay_db),
    }

    if _scoda_pkg:
        info['source_type'] = 'scoda'
        info['scoda_path'] = _scoda_pkg.scoda_path
        info['version'] = _scoda_pkg.version
        info['name'] = _scoda_pkg.name
        info['title'] = _scoda_pkg.title
        info['record_count'] = _scoda_pkg.record_count
    else:
        info['source_type'] = 'db'
        info['scoda_path'] = None

    return info


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(file_path):
    """Calculate SHA-256 of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()
