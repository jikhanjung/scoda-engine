# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SCODA Desktop standalone executables

Two executables are produced:
  ScodaDesktop.exe     - GUI viewer (console=False, no console blocking)
  ScodaMCP.exe - MCP stdio server (console=True, for Claude Desktop)

Build with: pyinstaller ScodaDesktop.spec
"""

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules
_uvicorn_imports = collect_submodules('uvicorn')

# ---------------------------------------------------------------------------
# ScodaDesktop.exe  (GUI viewer)
# ---------------------------------------------------------------------------
a = Analysis(
    ['launcher_gui.py'],
    pathex=['core'],
    binaries=[],
    datas=[
        ('scoda_engine', 'scoda_engine'),
    ],
    hiddenimports=[
        'scoda_engine',
        'scoda_engine.gui',
        'scoda_engine.scoda_package',
        'scoda_engine.app',
        'scoda_engine.mcp_server',
        'scoda_engine.serve',
        'scoda_engine_core',
        'scoda_engine_core.scoda_package',
        'fastapi',
        'fastapi.responses',
        'fastapi.staticfiles',
        'fastapi.templating',
        'fastapi.middleware.cors',
        'sqlite3',
        'json',
        'webbrowser',
        'threading',
    ] + _uvicorn_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScodaDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI subsystem: no console window, no blocking from PowerShell/cmd
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# ---------------------------------------------------------------------------
# ScodaMCP.exe  (MCP stdio server for Claude Desktop)
# ---------------------------------------------------------------------------
mcp_a = Analysis(
    ['launcher_mcp.py'],
    pathex=['core'],
    binaries=[],
    datas=[
        ('scoda_engine/scoda_package.py', 'scoda_engine'),
        ('scoda_engine/__init__.py', 'scoda_engine'),
    ],
    hiddenimports=[
        'scoda_engine',
        'scoda_engine.mcp_server',
        'scoda_engine.scoda_package',
        'scoda_engine_core',
        'scoda_engine_core.scoda_package',
        'mcp',
        'mcp.server',
        'mcp.server.stdio',
        'mcp.server.sse',
        'starlette',
        'starlette.applications',
        'starlette.routing',
        'starlette.responses',
        'sqlite3',
        'json',
    ] + _uvicorn_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

mcp_pyz = PYZ(mcp_a.pure, mcp_a.zipped_data, cipher=block_cipher)

mcp_exe = EXE(
    mcp_pyz,
    mcp_a.scripts,
    mcp_a.binaries,
    mcp_a.zipfiles,
    mcp_a.datas,
    [],
    name='ScodaMCP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Required for stdin/stdout MCP stdio communication
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
