#!/usr/bin/env bash
# Deterministisches Prüf-Gate. Wird vom coder, von den Reviewern und vom Autopilot genutzt.
# Exit 0 = alles grün. Ausgabe ist bewusst knapp und maschinenlesbar (=== <step>: OK|FEHLGESCHLAGEN).
#   CHECK_BUILD=0 bash scripts/check.sh   -> ohne `next build` (schneller)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT=$PWD

if [ ! -f web/package.json ]; then
  echo "=== setup: FEHLGESCHLAGEN – web/package.json fehlt. Erst 'bash scripts/bootstrap-web.sh' ausführen."
  exit 1
fi
cd web || exit 2
export CI=1 NEXT_TELEMETRY_DISABLED=1

if [ ! -d node_modules ] || [ package.json -nt node_modules ] || [ package-lock.json -nt node_modules ]; then
  echo "=== install: npm install"
  npm install --no-audit --no-fund --loglevel=error || { echo "=== install: FEHLGESCHLAGEN"; exit 1; }
  touch node_modules
fi

FAILED=()
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT
step() {
  local name=$1; shift
  echo "=== $name: $*"
  "$@" > "$LOG" 2>&1
  local rc=$?
  tail -n 60 "$LOG"
  if [ $rc -eq 0 ]; then echo "=== $name: OK"; else echo "=== $name: FEHLGESCHLAGEN (exit $rc)"; FAILED+=("$name"); fi
}

step typecheck npm run -s typecheck
step lint npm run -s lint
step test npm run -s test

# DB-Integrationstests nur, wenn vorhanden und Postgres erreichbar ist.
if npm pkg get scripts.test:db | grep -qv '{}' && (echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null; then
  step test-db npm run -s test:db
fi

if [ "${CHECK_BUILD:-1}" = "1" ]; then
  step build npm run -s build
fi

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "CHECK RESULT: PASS"
  exit 0
fi
echo "CHECK RESULT: FAIL (${FAILED[*]})"
exit 1
