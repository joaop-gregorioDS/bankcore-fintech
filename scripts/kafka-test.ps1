[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$composeFile = Join-Path $PSScriptRoot "..\docker-compose.kafka-test.yml"
$projectName = "bankcore-kafka-test-$([guid]::NewGuid().ToString('N'))"
$topic = "bankcore.transaction.completed.v1"
$eventId = [guid]::NewGuid().ToString()
$eventIdAfterRestart = [guid]::NewGuid().ToString()
$exitCode = 1

function Invoke-Compose {
    param([string[]]$Arguments)
    & docker compose -p $projectName -f $composeFile @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose step failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Kafka {
    param([string]$Tool, [string[]]$Arguments)
    $output = & docker compose -p $projectName -f $composeFile exec -T kafka "/opt/kafka/bin/$Tool" @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Kafka command '$Tool' failed with exit code $LASTEXITCODE."
    }
    return $output
}

function Publish-Event {
    param([string]$Message)
    $encodedMessage = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Message))
    & docker compose -p $projectName -f $composeFile exec -T kafka `
        sh -c "printf '%s' '$encodedMessage' | base64 -d | /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic $topic"
    if ($LASTEXITCODE -ne 0) {
        throw "Kafka producer failed with exit code $LASTEXITCODE."
    }
}

function Assert-EventConsumed {
    param([string]$ExpectedMessage, [int]$MaxMessages = 1)
    $output = & docker compose -p $projectName -f $composeFile exec -T kafka `
        /opt/kafka/bin/kafka-console-consumer.sh `
        --bootstrap-server kafka:9092 `
        --topic $topic `
        --from-beginning `
        --max-messages $MaxMessages `
        --timeout-ms 15000 `
        2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Kafka consumer failed with exit code $LASTEXITCODE."
    }
    $actual = ($output -join "`n").Trim()
    if ($actual -notmatch [regex]::Escape($ExpectedMessage)) {
        throw "Kafka consumer did not receive the expected event. Expected: $ExpectedMessage; Actual: $actual"
    }
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not available."
    }

    Invoke-Compose @("config", "-q")
    Invoke-Compose @("up", "-d", "--wait", "kafka")

    Invoke-Kafka "kafka-topics.sh" @(
        "--bootstrap-server", "kafka:9092",
        "--create", "--if-not-exists",
        "--topic", $topic,
        "--partitions", "1",
        "--replication-factor", "1"
    ) | Out-Null

    $description = Invoke-Kafka "kafka-topics.sh" @(
        "--bootstrap-server", "kafka:9092",
        "--describe", "--topic", $topic
    )
    if (($description -join "`n") -notmatch [regex]::Escape($topic)) {
        throw "Expected topic '$topic' was not found."
    }

    $message = '{"event_id":"' + $eventId + '","event_type":"transaction.completed","event_version":1}'
    Publish-Event $message
    Assert-EventConsumed $message

    Invoke-Compose @("restart", "kafka")
    Invoke-Compose @("up", "-d", "--wait", "kafka")

    $descriptionAfterRestart = Invoke-Kafka "kafka-topics.sh" @(
        "--bootstrap-server", "kafka:9092",
        "--describe", "--topic", $topic
    )
    if (($descriptionAfterRestart -join "`n") -notmatch [regex]::Escape($topic)) {
        throw "Topic '$topic' was not available after broker restart."
    }

    $messageAfterRestart = '{"event_id":"' + $eventIdAfterRestart + '","event_type":"transaction.completed","event_version":1}'
    Publish-Event $messageAfterRestart
    Assert-EventConsumed $messageAfterRestart 2

    Write-Output "Kafka KRaft smoke test passed: topic '$topic' survived restart and synthetic events were produced and consumed."
    $exitCode = 0
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
