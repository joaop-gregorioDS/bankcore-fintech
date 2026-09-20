[CmdletBinding()]
param([switch]$KeepArtifacts)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "docker-compose.backup.yml"
$projectName = "bankcore-backup-$([guid]::NewGuid().ToString('N'))"
$artifactDir = Join-Path $repoRoot "artifacts\p1d-$([guid]::NewGuid().ToString('N'))"
$env:BACKUP_POSTGRES_PASSWORD = "backup-$([guid]::NewGuid().ToString('N'))"
$env:BACKUP_ARTIFACT_DIR = $artifactDir
$exitCode = 1

try {
    New-Item -ItemType Directory -Path $artifactDir -Force | Out-Null
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker Desktop is not available." }
    & docker compose -p $projectName -f $composeFile build
    if ($LASTEXITCODE -ne 0) { throw "Backup test image build failed." }
    & docker compose -p $projectName -f $composeFile up -d --wait backup-source backup-target
    if ($LASTEXITCODE -ne 0) { throw "Disposable PostgreSQL startup failed." }
    & docker compose -p $projectName -f $composeFile run --rm backup-runner
    $exitCode = $LASTEXITCODE
}
catch { Write-Error $_ }
finally {
    & docker compose -p $projectName -f $composeFile down -v --remove-orphans *> $null
    if (-not $KeepArtifacts -and (Test-Path -LiteralPath $artifactDir)) {
        Remove-Item -LiteralPath $artifactDir -Recurse -Force
    }
    if ($LASTEXITCODE -ne 0 -and $exitCode -eq 0) { $exitCode = 1 }
}

exit $exitCode
