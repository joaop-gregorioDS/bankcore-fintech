#!/usr/bin/env bash
set -u

compose_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docker-compose.kafka-test.yml"
project="bankcore-kafka-test-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
topic="bankcore.transaction.completed.v1"
event_id="$(cat /proc/sys/kernel/random/uuid)"
event_id_after_restart="$(cat /proc/sys/kernel/random/uuid)"
exit_code=1

cleanup() {
  docker compose -p "$project" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || {
    [ "$exit_code" -eq 0 ] && exit_code=1
  }
}
trap cleanup EXIT

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not available." >&2
  exit "$exit_code"
fi

docker compose -p "$project" -f "$compose_file" config -q || exit "$exit_code"
docker compose -p "$project" -f "$compose_file" up -d --wait kafka || exit "$exit_code"

docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server kafka:9092 \
  --create --if-not-exists \
  --topic "$topic" --partitions 1 --replication-factor 1 || exit "$exit_code"

description="$(docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic "$topic")" || exit "$exit_code"
grep -Fq "$topic" <<< "$description" || { echo "Topic was not created." >&2; exit "$exit_code"; }

message="{\"event_id\":\"$event_id\",\"event_type\":\"transaction.completed\",\"event_version\":1}"
printf '%s\n' "$message" | docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic "$topic" || exit "$exit_code"

consumed="$(docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic "$topic" --from-beginning --max-messages 1 --timeout-ms 15000 2>/dev/null)" || exit "$exit_code"
grep -Fq "$message" <<< "$consumed" || { echo "Consumer did not receive the expected event." >&2; exit "$exit_code"; }

docker compose -p "$project" -f "$compose_file" restart kafka || exit "$exit_code"
docker compose -p "$project" -f "$compose_file" up -d --wait kafka || exit "$exit_code"

description_after_restart="$(docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --describe --topic "$topic")" || exit "$exit_code"
grep -Fq "$topic" <<< "$description_after_restart" || { echo "Topic was not available after restart." >&2; exit "$exit_code"; }

message_after_restart="{\"event_id\":\"$event_id_after_restart\",\"event_type\":\"transaction.completed\",\"event_version\":1}"
printf '%s\n' "$message_after_restart" | docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-console-producer.sh --bootstrap-server kafka:9092 --topic "$topic" || exit "$exit_code"

consumed_after_restart="$(docker compose -p "$project" -f "$compose_file" exec -T kafka \
  /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 \
  --topic "$topic" --from-beginning --max-messages 2 --timeout-ms 15000 2>/dev/null)" || exit "$exit_code"
grep -Fq "$message_after_restart" <<< "$consumed_after_restart" || { echo "Consumer did not receive the post-restart event." >&2; exit "$exit_code"; }

echo "Kafka KRaft smoke test passed: topic '$topic' survived restart and synthetic events were produced and consumed."
exit_code=0
