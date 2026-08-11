# GPUProvider Windows packaging

Build the single-file, windowed executable from the repository root:

```powershell
.\packaging\build.ps1
```

The script uses `agent\env\Scripts\python.exe`, installs PyInstaller into that
virtualenv, and writes the result to `packaging\dist\GPUProvider.exe`. The
specification packages only the `agent.app` import graph. It has no data files:
the tray icon is created with PIL at runtime. It does not collect the
repository, `agent\env`, `web-client`, or `services`.

`agent.core` is absent from the current build simply because nothing imports it
yet. That is import-graph analysis doing its job, not an exclusion — the spec
deliberately sets `excludes=[]`, so the modules appear automatically once
leases and metering are wired in. Naming them in `excludes` would have made the
frozen build raise `ImportError` at exactly the moment the source build started
working, and a packaging file must not be what decides which modules the
application is allowed to import.

Verified build: 18 MB, launches with no console window, ~9 MB resident.

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
