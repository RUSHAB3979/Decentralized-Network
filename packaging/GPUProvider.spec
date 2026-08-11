# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller configuration for the Windows GPU Provider app."""

from pathlib import Path

import webview


PROJECT_ROOT = Path(SPEC).resolve().parent.parent

# The dashboard is a Vite build, not source. `npm run build:desktop` in
# web-client/ writes it here. Fail loudly rather than shipping an exe whose
# window opens blank, which is what a missing bundle looks like at runtime:
# pywebview loads a file:// URL that does not exist and paints nothing.
DESKTOP_BUNDLE = PROJECT_ROOT / "agent" / "ui" / "web"
if not (DESKTOP_BUNDLE / "desktop.html").is_file():
    raise SystemExit(
        f"Desktop bundle missing at {DESKTOP_BUNDLE}.\n"
        "Run: cd web-client && npm run build:desktop"
    )

# pywebview reaches for its .NET interop assemblies by filesystem path, not by
# import, so PyInstaller's analysis cannot see them. Worse, the frozen lookup in
# webview/util.py:interop_dll_path expects a *flat* layout - sys._MEIPASS/<dll>
# - not the webview/lib/ tree it uses from source. Copying the package layout
# verbatim would place the files where nothing looks for them.
WEBVIEW_LIB = Path(webview.__file__).resolve().parent / "lib"
WEBVIEW_DATAS = [
    (str(WEBVIEW_LIB / "Microsoft.Web.WebView2.Core.dll"), "."),
    (str(WEBVIEW_LIB / "Microsoft.Web.WebView2.WinForms.dll"), "."),
    (str(WEBVIEW_LIB / "WebBrowserInterop.x64.dll"), "."),
]
# edgechromium.py appends sys._MEIPASS/<rid> to PATH for each of these, so the
# loader has to sit one directory down under the RID name.
for rid in ("win-arm64", "win-x64", "win-x86"):
    WEBVIEW_DATAS.append((str(WEBVIEW_LIB / "runtimes" / rid / "native" / "WebView2Loader.dll"), rid))

a = Analysis(
    [str(PROJECT_ROOT / "agent" / "app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[(str(DESKTOP_BUNDLE), "agent/ui/web"), *WEBVIEW_DATAS],
    # All three are selected at runtime by string, never imported statically:
    # pystray picks its backend from the platform, and pywebview's guilib walks
    # a list of import_* functions. Static analysis finds none of them.
    hiddenimports=[
        "pystray._win32",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ],
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
