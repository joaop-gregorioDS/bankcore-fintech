[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.outbox-test.yml"
$projectName = "bankcore-outbox-test-$([guid]::NewGuid().ToString('N'))"
$env:COMPOSE_PROJECT_NAME = $projectName
$env:TEST_POSTGRES_PASSWORD = "test-$([guid]::NewGuid().ToString('N'))"
$exitCode = 1

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose -p $projectName -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Outbox test environment step failed with exit code $LASTEXITCODE."
    }
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not available."
    }

    Invoke-Compose @("config", "-q")
    Invoke-Compose @("build")
    Invoke-Compose @("up", "-d", "--wait", "postgres-test", "kafka")
    Invoke-Compose @("run", "--rm", "migrate-transactions-test")
    & docker compose -p $projectName -f $composeFile run --rm --no-deps publisher-tests
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Error $_
}
finally {
    docker compose -p $projectName -f $composeFile down -v --remove-orphans *> $null
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) {
        $exitCode = 1
    }
}

exit $exitCode
