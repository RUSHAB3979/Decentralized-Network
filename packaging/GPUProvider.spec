# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller configuration for the Windows GPU Provider tray application."""

from pathlib import Path


PROJECT_ROOT = Path(SPEC).resolve().parent.parent

a = Analysis(
    [str(PROJECT_ROOT / "agent" / "app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=["pystray._win32"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # agent.core is not imported on the boot path today, but excluding it makes
    # the frozen build diverge from the source build: the moment leases or
    # metering get wired in, `python -m agent.app` keeps working and the exe
    # raises ImportError. A packaging config must not be the thing that decides
    # what the app can import.
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GPUProvider",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX stays OFF. Executable packers are one of the strongest heuristic
    # triggers for antivirus false positives, and this app's whole distribution
    # problem (see README.md) is being flagged by Defender and SmartScreen.
    # Trading a few MB for a detection we then have to appeal is a bad trade.
    upx=False,
    console=False,
)
