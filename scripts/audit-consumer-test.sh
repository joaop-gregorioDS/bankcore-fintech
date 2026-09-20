#!/usr/bin/env bash
set -u

compose_file="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docker-compose.audit-test.yml"
project="bankcore-audit-test-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
export COMPOSE_PROJECT_NAME="$project"
export TEST_POSTGRES_PASSWORD="test-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
exit_code=1

if docker info >/dev/null 2>&1; then
  docker compose -p "$project" -f "$compose_file" config -q
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f "$compose_file" build; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f "$compose_file" up -d --wait postgres-test kafka; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f "$compose_file" run --rm migrate-transactions-test; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f "$compose_file" run --rm migrate-audit-test; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f "$compose_file" run --rm --no-deps audit-tests; exit_code=$?; fi
else
  echo "Docker is not available." >&2
fi

docker compose -p "$project" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || {
  [ "$exit_code" -eq 0 ] && exit_code=1
}
exit "$exit_code"
