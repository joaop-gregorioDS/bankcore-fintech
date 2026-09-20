[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
python (Join-Path $PSScriptRoot "p4-rate-limit.py")
exit $LASTEXITCODE
