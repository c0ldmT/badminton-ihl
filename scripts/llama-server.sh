#!/usr/bin/env bash
# OPTIONALES Performance-Profil: Qwen3.6-35B-A3B über llama.cpp mit gezielter Auslagerung
# der MoE-Experten auf die CPU (--n-cpu-moe). Ollama bietet diese Stellschraube nicht.
# Nicht auf deiner Hardware getestet – Startwerte, bitte tunen (README Anhang A).
#
#   sudo systemctl stop ollama      # beide Server gleichzeitig passen nicht in 12 GB VRAM
#   bash scripts/llama-server.sh
set -euo pipefail
LLAMA_BIN=${LLAMA_BIN:-$HOME/llama.cpp/build/bin/llama-server}
MODEL_HF=${MODEL_HF:-unsloth/Qwen3.6-35B-A3B-GGUF:UD-Q4_K_XL}
CTX=${CTX:-65536}
# Anzahl der Schichten (von 40), deren Experten im RAM bleiben. Kleiner = mehr auf der GPU = schneller.
# Bei "out of memory" erhöhen, bei viel freiem VRAM (nvidia-smi) senken.
N_CPU_MOE=${N_CPU_MOE:-28}
THREADS=${THREADS:-8}          # i7-12700KF: 8 P-Kerne

[ -x "$LLAMA_BIN" ] || { echo "llama-server nicht gefunden: $LLAMA_BIN (README Anhang A)"; exit 1; }

exec "$LLAMA_BIN" \
  -hf "$MODEL_HF" --no-mmproj \
  --alias qwen3.6-35b-a3b \
  --jinja \
  -c "$CTX" --parallel 1 \
  -ngl 999 --n-cpu-moe "$N_CPU_MOE" \
  -fa on --cache-type-k q8_0 --cache-type-v q8_0 \
  -t "$THREADS" \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 \
  --host 127.0.0.1 --port 8080
