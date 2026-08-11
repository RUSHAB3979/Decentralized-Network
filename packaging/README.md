# GPUProvider Windows packaging

Build the single-file, windowed executable from the repository root. The
dashboard is a Vite build, so it has to exist before PyInstaller runs:

```powershell
cd web-client; npm run build:desktop; cd ..
.\packaging\build.ps1
```

The script uses `agent\env\Scripts\python.exe`, installs PyInstaller into that
virtualenv, and writes the result to `packaging\dist\GPUProvider.exe`. It does
not collect the repository, `agent\env`, `web-client` sources, or `services` —
only the `agent.app` import graph plus two sets of data files.

## What the spec ships as data, and why it has to

The tray icon is still drawn with PIL at runtime and is still not a data file.
The two that are:

**`agent\ui\web\`** — the compiled dashboard. `pywebview` loads it as a
`file://` URL, so it is read from disk at runtime rather than imported, and
import-graph analysis cannot see it. If it is missing the window opens and
paints nothing, with no error anywhere. The spec therefore checks for
`desktop.html` and aborts the build rather than producing an executable whose
only symptom is a blank window.

**pywebview's .NET interop assemblies** — `Microsoft.Web.WebView2.Core.dll`,
`Microsoft.Web.WebView2.WinForms.dll`, `WebBrowserInterop.x64.dll`, and a
`WebView2Loader.dll` per architecture. These are loaded by path through
`clr.AddReference`, which is again invisible to analysis.

The layout matters and is not the obvious one. `webview\util.py`'s frozen-path
branch looks for the assemblies **flat at `sys._MEIPASS`**, not under the
`webview\lib\` tree they occupy in site-packages, and `edgechromium.py` appends
`sys._MEIPASS\win-x64` (and the arm64/x86 equivalents) to `PATH` for the
loaders. Mirroring the source layout would put every file somewhere nothing
looks, and the failure surfaces as a .NET `FileNotFoundException` at import
time, in the frozen build only.

`hiddenimports` carries `pystray._win32`, `webview.platforms.winforms` and
`webview.platforms.edgechromium` for the same underlying reason: all three are
chosen at runtime by string — pystray from the platform, pywebview by walking a
list of `import_*` functions in `guilib.py` — so none appears in the graph.

`agent.core` is absent from the current build simply because nothing imports it
yet. That is import-graph analysis doing its job, not an exclusion — the spec
deliberately sets `excludes=[]`, so the modules appear automatically once
leases and metering are wired in. Naming them in `excludes` would have made the
frozen build raise `ImportError` at exactly the moment the source build started
working, and a packaging file must not be what decides which modules the
application is allowed to import.

Verified build (2026-08-11): 23.6 MB, launches with no console window.

Read the resident figure carefully. A one-file build runs as two processes: the
bootloader parent, which sits at roughly 8 MB and owns no window, and the child
that actually runs Python and owns the "GPU Provider" window at roughly 121 MB.
WebView2 spawns its own helper processes on top of that, which are not counted
here at all. Checking only the parent makes the app look far lighter than it is
and, worse, makes a working build look like a broken one — the parent's
`MainWindowTitle` is always empty.

## Why UPX is disabled

The spec sets `upx=False` deliberately. Executable packers are among the
strongest heuristic triggers for the antivirus detections described below, and
this application's entire distribution problem is being flagged by Defender and
SmartScreen. Compressing a few megabytes off an 18 MB download in exchange for
a detection that then has to be appealed is a bad trade. Do not turn it on
without measuring the detection rate both ways.

## Defender and SmartScreen

PyInstaller one-file programs routinely receive antivirus heuristic detections.
The bootloader unpacks the embedded application to a temporary directory at
launch, a behavior that can resemble malware. A detection can be a false
positive, but it must be investigated; do not tell users to disable Defender.

SmartScreen is a related but distinct download/reputation check. Microsoft says
it considers both publisher-certificate reputation and the file hash. An
unsigned executable starts without either publisher reputation or a trusted
publisher name. [Microsoft's SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation)
also makes two important points: a new signed binary can still warn, and EV
certificates no longer receive an automatic SmartScreen-reputation bypass.

Concrete options and costs:

| Option | What it does | Real cost and limitation |
| --- | --- | --- |
| Authenticode OV certificate | Signs releases under an organization-validated publisher name. | Roughly USD 150-400 per year, plus identity-validation time and protected-key storage/service costs. It does not guarantee removal of Defender detections or SmartScreen warnings. |
| Authenticode EV certificate | Stronger organization validation; commonly requires a hardware token or managed signing service. | Roughly USD 300-700 per year, plus validation and token/service friction. Do not buy EV solely for SmartScreen: Microsoft says it no longer bypasses warnings. |
| Build `--onedir` instead | Avoids the one-file self-extraction behavior. | It may reduce a particular heuristic detection, but there is no Microsoft or PyInstaller guarantee that it reduces flagging. It also ships a directory of files, so it does not meet this single-exe deliverable. |
| Build reputation | Keep the same publisher identity, sign every release, and distribute cleanly. | There is no guaranteed time or threshold. Microsoft says it can take several weeks and hundreds of clean installs from a wide audience; every new unsigned hash starts from zero. |

If Defender identifies a clean release as malware, submit the exact released
binary as a software-developer false positive through the
[Microsoft Security Intelligence file-submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission).
That review can correct a Defender classification; it is not a shortcut for
creating SmartScreen reputation. Re-submit after a materially changed build if
the classification returns.
