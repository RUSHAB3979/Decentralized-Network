[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot "agent\env\Scripts\python.exe"
$pip = Join-Path $projectRoot "agent\env\Scripts\pip.exe"
$spec = Join-Path $PSScriptRoot "GPUProvider.spec"
$build = Join-Path $PSScriptRoot "build"
$dist = Join-Path $PSScriptRoot "dist"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Virtualenv Python was not found at agent\\env\\Scripts\\python.exe."
}

& $pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Installing PyInstaller failed with exit code $LASTEXITCODE."
}

& $python -m PyInstaller --noconfirm --clean --workpath $build --distpath $dist $spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$exe = Join-Path $dist "GPUProvider.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build completed but did not produce packaging\\dist\\GPUProvider.exe."
}

Write-Output "Built $exe"
