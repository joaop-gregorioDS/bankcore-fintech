#!/usr/bin/env bash
set -u

keep_artifacts="false"
[ "${1:-}" = "--keep-artifacts" ] && keep_artifacts="true"
project="bankcore-backup-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
artifact_dir="$(pwd)/artifacts/p1d-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
export COMPOSE_PROJECT_NAME="$project"
export BACKUP_POSTGRES_PASSWORD="backup-$(cat /proc/sys/kernel/random/uuid | tr -d '-')"
export BACKUP_ARTIFACT_DIR="$artifact_dir"
exit_code=1

mkdir -p "$artifact_dir"
if docker info >/dev/null 2>&1; then
  docker compose -p "$project" -f docker-compose.backup.yml build
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.backup.yml up -d --wait backup-source backup-target; exit_code=$?; fi
  if [ "$exit_code" -eq 0 ]; then docker compose -p "$project" -f docker-compose.backup.yml run --rm backup-runner; exit_code=$?; fi
else
  echo "Docker is not available." >&2
fi
docker compose -p "$project" -f docker-compose.backup.yml down -v --remove-orphans >/dev/null 2>&1 || { [ "$exit_code" -eq 0 ] && exit_code=1; }
[ "$keep_artifacts" = "true" ] || rm -rf -- "$artifact_dir"
exit "$exit_code"
