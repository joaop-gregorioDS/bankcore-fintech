[CmdletBinding()]
param(
    [ValidateSet("all", "unit", "security", "integration", "postgres")]
    [string]$Suite = "all",
    [switch]$ForceFailure
)

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.test.yml"
$projectName = "bankcore-test-$([guid]::NewGuid().ToString('N'))"
$env:COMPOSE_PROJECT_NAME = $projectName
$env:TEST_POSTGRES_PASSWORD = "test-$([guid]::NewGuid().ToString('N'))"
$env:TEST_SUITE = $Suite
$env:TEST_FORCE_FAILURE = $ForceFailure.ToString().ToLower()
$exitCode = 1

function Invoke-ComposeStep {
    param([string[]]$Arguments)
    & docker compose -p $projectName -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Test environment step failed with exit code $LASTEXITCODE."
    }
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not available."
    }

    Invoke-ComposeStep @("build")
    Invoke-ComposeStep @("up", "-d", "--wait", "postgres-test")
    Invoke-ComposeStep @("run", "--rm", "migrate-auth-test")
    Invoke-ComposeStep @("run", "--rm", "migrate-transactions-test")
    & docker compose -p $projectName -f $composeFile run --rm --no-deps test-runner
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
