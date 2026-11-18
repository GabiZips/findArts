# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import PureWindowsPath

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = (
    collect_submodules("sources")
    + collect_submodules("filters")
    + collect_submodules("utils")
    + collect_submodules("artfinder")
    + ["keyring.backends.Windows" if sys.platform == "win32" else "keyring.backends.SecretService"]
)

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("templates", "templates"),
        ("palettes", "palettes"),
        ("assets/artfinder-icon.png", "assets"),
        ("assets/artfinder.ico", "assets"),
        ("assets/fonts", "assets/fonts"),
        ("defaults/categories.json", "defaults"),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["webview", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
              "PySide6.QtWebEngineQuick", "PySide6.QtPdf", "PySide6.QtPdfWidgets"],
    noarchive=False,
    optimize=0,
)
if sys.platform == "win32":
    # Qt 6 uses the Windows ICU API (unversioned exports such as ucnv_open).
    # A foreign icuuc.dll on PATH, e.g. from Poppler/Conda, exposes renamed
    # symbols and shadows the OS library in a frozen app (WinError 127).
    # Windows 10+ supplies these libraries; never bundle a PATH lookalike.
    a.binaries = [
        entry for entry in a.binaries
        if PureWindowsPath(entry[0]).name.lower() not in {"icu.dll", "icuuc.dll", "icuin.dll"}
        and not PureWindowsPath(entry[0]).name.lower().startswith("icudt")
    ]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ArtFinder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["assets/artfinder-desktop.ico"] if sys.platform == "win32" else None,
)
