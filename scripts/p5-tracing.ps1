$ErrorActionPreference = "Stop"
python (Join-Path $PSScriptRoot "p5-tracing.py")
exit $LASTEXITCODE
