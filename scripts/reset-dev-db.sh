#!/usr/bin/env bash
# Setzt die Dev-Datenbank auf den Stand der committeten Migrationen zurück.
# Wird vom Autopilot nach einem Rollback genutzt, wenn die verworfene Task Migrationen enthielt.
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f compose.dev.yml exec -T postgres \
  psql -U liga -d liga -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS drizzle CASCADE; DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
if [ -f web/package.json ] && (cd web && npm pkg get scripts.db:migrate | grep -qv '{}'); then
  (cd web && npm run -s db:migrate)
fi
echo "Dev-DB zurückgesetzt."
