#!/usr/bin/env bash
set -u

suite="${1:-all}"
case "$suite" in
  all|unit|security|integration|postgres) ;;
  *) echo "usage: $0 [all|unit|security|integration|postgres]" >&2; exit 2 ;;
esac

project="bankcore-test-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
export COMPOSE_PROJECT_NAME="$project"
export TEST_POSTGRES_PASSWORD="test-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
export TEST_SUITE="$suite"
exit_code=1

if docker info >/dev/null 2>&1; then
  docker compose -p "$project" -f docker-compose.test.yml build
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.test.yml up -d --wait postgres-test; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.test.yml run --rm migrate-auth-test; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.test.yml run --rm migrate-transactions-test; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.test.yml run --rm --no-deps test-runner; exit_code=$?; fi
else
  echo "Docker is not available." >&2
fi

docker compose -p "$project" -f docker-compose.test.yml down -v --remove-orphans >/dev/null 2>&1 || {
  [ "$exit_code" -eq 0 ] && exit_code=1
}
exit "$exit_code"
