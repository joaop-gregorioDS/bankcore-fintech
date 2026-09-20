[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.audit-test.yml"
$projectName = "bankcore-audit-retry-test-$([guid]::NewGuid().ToString('N'))"
$env:COMPOSE_PROJECT_NAME = $projectName
$env:TEST_POSTGRES_PASSWORD = "test-$([guid]::NewGuid().ToString('N'))"
$exitCode = 1

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose -p $projectName -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Audit retry test environment step failed with exit code $LASTEXITCODE."
    }
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not available." }
    Invoke-Compose @("config", "-q")
    Invoke-Compose @("build")
    Invoke-Compose @("up", "-d", "--wait", "postgres-test", "kafka")
    Invoke-Compose @("run", "--rm", "migrate-transactions-test")
    Invoke-Compose @("run", "--rm", "migrate-audit-test")
    & docker compose -p $projectName -f $composeFile run --rm --no-deps audit-tests python -m pytest -q tests/p3f_retry_dlq_tests.py
    $exitCode = $LASTEXITCODE
}
catch { Write-Error $_ }
finally {
    docker compose -p $projectName -f $composeFile down -v --remove-orphans *> $null
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) { $exitCode = 1 }
}

exit $exitCode
