#!/usr/bin/env bash
# Copie la BDD distante (identifiants DB_* du .env) dans le Postgres local docker.
# Lecture seule côté distant (pg_dump). ÉCRASE la base locale.
#   ./scripts/db_pull_remote.sh
set -euo pipefail
export COMPOSE_DISABLE_ENV_FILE=1
cd "$(dirname "$0")/.."

get() { grep -E "^$1=" .env | head -1 | cut -d= -f2- | sed -E "s/^[\"'](.*)[\"']$/\1/"; }
R_HOST=$(get DB_HOST); R_PORT=$(get DB_PORT); R_USER=$(get DB_USER)
R_PASS=$(get DB_PASSWORD); R_NAME=$(get DB_NAME)

mkdir -p .local
DUMP=.local/remote.dump

echo "→ Dump de $R_HOST:$R_PORT/$R_NAME"
docker run --rm -e PGPASSWORD="$R_PASS" -v "$PWD/.local:/out" postgres:18 \
  pg_dump -h "$R_HOST" -p "$R_PORT" -U "$R_USER" -d "$R_NAME" \
  -Fc --no-owner --no-acl -f /out/remote.dump

echo "→ Démarrage du Postgres local"
docker compose -f docker-compose.local.yml up -d --wait db

echo "→ Restauration dans la base locale"
docker compose -f docker-compose.local.yml exec -T db \
  psql -U lylo -d postgres -c "DROP DATABASE IF EXISTS lylo WITH (FORCE);" -c "CREATE DATABASE lylo;"
docker compose -f docker-compose.local.yml exec -T db \
  pg_restore -U lylo -d lylo --no-owner --no-acl < "$DUMP"

echo "✓ Base locale à jour ($DUMP)"
