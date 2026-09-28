#!/usr/bin/env bash
# Prüft die WSL-Umgebung. Aufruf aus dem Projektroot:  bash scripts/verify-setup.sh [--warmup]
#   --warmup  lädt das Modell einmal und zeigt die GPU/CPU-Verteilung (dauert 1-3 min)
cd "$(dirname "$0")/.." || exit 2
FAIL=0
ok()   { echo "  [OK]      $1"; }
bad()  { echo "  [FEHLT]   $1"; FAIL=1; }
warn() { echo "  [WARNUNG] $1"; }
info() { echo "  [INFO]    $1"; }

MODEL=qwen3.6:35b
[ -f autopilot/.env ] && M=$(grep -E '^LLM_MODEL=' autopilot/.env | cut -d= -f2) && [ -n "$M" ] && MODEL=$M
BASE=http://localhost:11434
[ -f autopilot/.env ] && B=$(grep -E '^LLM_BASE_URL=' autopilot/.env | cut -d= -f2) && [ -n "$B" ] && BASE=${B%/v1}

echo "== Umgebung =="
grep -qi microsoft /proc/version && ok "läuft in WSL" || warn "nicht in WSL erkannt"
case "$PWD" in /mnt/*) bad "Projekt liegt unter /mnt/... (langsam) -> nach ~/projects verschieben";; *) ok "Projekt im Linux-Dateisystem";; esac
[ "$(ps -p 1 -o comm= 2>/dev/null)" = "systemd" ] && ok "systemd aktiv" || bad "systemd nicht aktiv (README 2.2)"
MEM=$(free -g | awk '/^Mem:/{print $2}'); [ "${MEM:-0}" -ge 22 ] && ok "WSL-RAM: ${MEM} GB" || warn "WSL-RAM nur ${MEM} GB – .wslconfig memory=24GB empfohlen (README 1.1)"
DISK=$(df -BG --output=avail "$HOME" | tail -1 | tr -dc 0-9); [ "${DISK:-0}" -ge 40 ] && ok "freier Speicher: ${DISK} GB" || warn "nur ${DISK} GB frei (Modelle ~30 GB)"

echo "== Tools =="
for c in git curl jq unzip zstd python3 docker ollama opencode node npm; do
  command -v $c >/dev/null && ok "$c" || bad "$c nicht installiert"
done
python3 -c "import venv" 2>/dev/null && ok "python3-venv" || bad "python3-venv"
if command -v node >/dev/null; then
  NV=$(node -p 'process.versions.node'); NM=${NV%%.*}
  [ "$NM" -ge 22 ] && ok "Node $NV" || { [ "$NM" -eq 20 ] && warn "Node $NV – 22 LTS empfohlen" || bad "Node $NV zu alt (>= 20.9, empfohlen 22)"; }
fi
if command -v opencode >/dev/null; then
  OV=$(opencode --version 2>/dev/null | tail -1)
  case "$OV" in 1.*) ok "OpenCode $OV";; *) warn "OpenCode $OV – getestet mit 1.18.x (README 7.2)";; esac
fi
command -v docker >/dev/null && { docker compose version >/dev/null 2>&1 && ok "docker compose" || bad "docker compose fehlt"; }
command -v docker >/dev/null && { docker info >/dev/null 2>&1 && ok "Docker-Daemon erreichbar" || bad "Docker-Daemon nicht erreichbar (Gruppe docker? neu einloggen)"; }

echo "== Git =="
[ -n "$(git config --global user.name)" ] && ok "user.name" || bad "git user.name nicht gesetzt"
[ -n "$(git config --global user.email)" ] && ok "user.email" || bad "git user.email nicht gesetzt"
git rev-parse HEAD >/dev/null 2>&1 && ok "Git-Repo mit Commit" || bad "kein Git-Repo/Commit (README 5.1)"
[ -f ~/.ssh/id_ed25519.pub ] && ok "SSH-Key vorhanden" || info "kein SSH-Key (nur für Remote-Push nötig)"

echo "== GPU =="
if command -v nvidia-smi >/dev/null && nvidia-smi >/dev/null 2>&1; then
  ok "$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader)"
else bad "GPU in WSL nicht sichtbar (Windows-Treiber aktualisieren, wsl --update)"; fi
ls /usr/lib/x86_64-linux-gnu/libnvidia-* >/dev/null 2>&1 && warn "Linux-NVIDIA-Treiberbibliotheken gefunden – in WSL nicht installieren (README 0)"

echo "== Ollama =="
if curl -sf "$BASE/api/tags" >/dev/null; then
  ok "Server erreichbar ($BASE), Version $(ollama --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)"
  ENVS=$(systemctl show ollama -p Environment 2>/dev/null)
  echo "$ENVS" | grep -q "OLLAMA_CONTEXT_LENGTH=65536" && ok "Kontext 65536" || warn "OLLAMA_CONTEXT_LENGTH nicht 65536 (README 6.1)"
  echo "$ENVS" | grep -q "OLLAMA_NUM_PARALLEL=1" && ok "NUM_PARALLEL=1" || warn "OLLAMA_NUM_PARALLEL nicht gesetzt (README 6.1)"
  if ollama list | awk '{print $1}' | grep -qx "$MODEL"; then
    ok "Modell $MODEL"
    ollama show "$MODEL" 2>/dev/null | grep -qi tools && ok "$MODEL: Tool-Support" || bad "$MODEL: kein 'tools' in Capabilities"
  else bad "Modell $MODEL fehlt (ollama pull $MODEL)"; fi
  if [ "${1:-}" = "--warmup" ]; then
    info "Lade $MODEL (kann dauern) …"
    curl -s "$BASE/api/generate" -d "{\"model\":\"$MODEL\",\"prompt\":\"Antworte nur mit ok\",\"stream\":false,\"think\":false}" | jq -r '.response' | head -c 80; echo
    ollama ps
    info "PROCESSOR zeigt die Aufteilung (z. B. 45%/55% CPU/GPU ist beim 35B-MoE normal), CONTEXT sollte 65536 sein."
  fi
else bad "Ollama nicht erreichbar (systemctl status ollama)"; fi

echo "== Projekt =="
for f in opencode.json AGENTS.md TASKS.md docs/PROJECT_SPEC.md compose.dev.yml scripts/check.sh autopilot/run.py .opencode/agents/coder.md; do
  [ -f "$f" ] && ok "$f" || bad "$f fehlt"
done
python3 autopilot/tasks.py list >/dev/null 2>&1 && ok "TASKS.md parsebar" || bad "TASKS.md hat Formatfehler (python3 autopilot/tasks.py list)"
[ -f web/package.json ] && ok "web/ vorhanden" || info "web/ noch nicht angelegt -> bash scripts/bootstrap-web.sh"
[ -d autopilot/.venv ] && ok "autopilot/.venv" || info "autopilot/.venv fehlt (README 10.1)"
(echo > /dev/tcp/127.0.0.1/5432) 2>/dev/null && ok "Postgres auf :5432" || info "Postgres nicht erreichbar -> docker compose -f compose.dev.yml up -d"

echo; [ $FAIL -eq 0 ] && echo "Alles bereit." || echo "Es gibt offene Punkte (siehe [FEHLT])."
exit $FAIL
