[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
python (Join-Path $root "scripts\p3-e2e.py")
exit $LASTEXITCODE
