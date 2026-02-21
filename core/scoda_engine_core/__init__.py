"""scoda_engine_core — pure-stdlib library for .scoda data packages."""

__version__ = "0.1.0"

from .scoda_package import (
    ScodaPackage, PackageRegistry,
    get_db, ensure_overlay_db, get_canonical_db_path, get_overlay_db_path,
    get_scoda_info, get_mcp_tools,
    set_active_package, get_active_package_name, get_registry,
    _set_paths_for_testing, _reset_paths, _reset_registry,
)
