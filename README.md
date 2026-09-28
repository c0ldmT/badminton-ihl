# Badminton-Liga – lokaler Agenten-Loop (WSL2, komplett offline-fähig)

Von einem frischen Windows-11-Rechner bis zum autonom laufenden
**Planner → Coder → Checks → Spec-Review → Quality-Review**-Loop, ausschließlich in
**WSL2 (Ubuntu 24.04)** und mit lokalem Modell.

> Zielsystem: Windows 11, i7-12700KF, 32 GB RAM, RTX 4070 Ti (12 GB VRAM).
> Fachliche Quelle der Wahrheit: `docs/PROJECT_SPEC.md` · Arbeitsstand: `TASKS.md` ·
> Änderungen gegenüber der Vorversion: `docs/CHANGES.md`

**Ablauf:** Windows vorbereiten → WSL → Basis-Pakete → Git → GPU prüfen → Projekt →
Ollama + Modell → Node.js + OpenCode → Docker → Web-Grundgerüst → Autopilot starten.
Reine Einrichtungszeit ca. 1–2 Stunden, davon viel Download (Modell ~23 GB).

---

## Wie das System arbeitet

```
            ┌──────── autopilot/run.py (Python + LangGraph, deterministisch) ────────┐
TASKS.md ─► Task wählen ─► Planner: Arbeitsauftrag ─► Coder ─► check.sh ─► Spec-Review ─► Quality-Review ─► git commit
                                                        ▲         │ rot       │ FAIL          │ FAIL
                                                        └─────────┴───────────┴───────────────┘
                                         nach 3 Fehlversuchen: Rollback, Patch sichern, Task = blocked
```

- **Ein Modell für alle Rollen.** Bei 12 GB VRAM würde jeder Wechsel zwischen verschiedenen
  Modellen ein Entladen/Neuladen und das Neuverarbeiten des Kontexts kosten. Die Rollen
  unterscheiden sich nur in Prompt und Rechten.
- **Code steuert, das Modell arbeitet.** Kleine lokale Modelle sind als Orchestrator
  unzuverlässig (Reviews werden übersprungen, der Kontext wächst von Task zu Task). Der
  Ablauf liegt daher im Python-Code; jeder LLM-Schritt startet mit frischem, kleinem Kontext.
- **Objektive Prüfung vor jedem Review.** `scripts/check.sh` (Typecheck, Lint, Tests, Build)
  muss grün sein, bevor ein LLM-Reviewer gefragt wird. Die Reviewer sehen den echten
  `git diff`, nicht nur die Selbstauskunft des Coders.
- **Git als Sicherheitsnetz.** Jede erfolgreiche Task ist ein Commit. Scheitert eine Task,
  wird auf den Stand davor zurückgesetzt und der Versuch als Patch aufbewahrt.

Zusätzlich gibt es einen **interaktiven Modus** in der OpenCode-Oberfläche (Abschnitt 11).
Beide Modi nutzen dieselben Rollen-Prompts aus `.opencode/agents/`.

### Modellprofile

| Profil | Modell | Speicher | Verteilung | Einsatz |
|---|---|---|---|---|
| **Standard** | `qwen3.6:35b` (Qwen3.6-35B-A3B, MoE, ~3B aktiv) via Ollama | ~23 GB | ca. halb GPU / halb RAM | Default – beste Code-Qualität, die auf diese Hardware passt |
| Leicht | `qwen3.5:9b` via Ollama | ~6,6 GB | 100 % GPU | schneller, aber deutlich schwächer; zum Testen des Setups oder bei RAM-Knappheit |
| Performance *(optional)* | Qwen3.6-35B-A3B (GGUF) via llama.cpp | ~22 GB | Attention auf GPU, Experten teils im RAM | gleiche Qualität wie Standard, meist schneller; mehr Einrichtung (Anhang A) |

Warum Qwen3.6-35B-A3B: auf agentisches Coding trainiert, Tool-Calls, und durch die hybride
Attention (nur jede 4. Schicht mit vollem KV-Cache) kostet ein 64k-Kontext weniger als 1 GB.
Weil pro Token nur ~3B Parameter aktiv sind, bleibt es trotz Auslagerung in den RAM benutzbar.

> **Erwartungsmanagement:** Die Geschwindigkeit konnte ich nicht auf deiner Maschine messen.
> Rechne grob mit 10–45 Minuten pro Task (Modell + `npm install` + Build). Ideal ist ein Lauf
> über Nacht. Auch ein gutes lokales Modell ist schwächer als Cloud-Modelle – deshalb sind die
> Tasks in `TASKS.md` klein geschnitten und haben prüfbare Akzeptanzkriterien.

---

## 0. Voraussetzungen (Windows-Seite)

1. **Windows 11** aktuell (`Win + R` → `winver`).
2. **Virtualisierung im BIOS/UEFI aktiv** (Intel VT-x; bei ASUS meist „Intel Virtualization
   Technology“ unter Advanced → CPU Configuration).
3. **Aktueller NVIDIA-Treiber unter Windows** (Game Ready oder Studio). Das ist der
   **einzige** Treiber, den du brauchst.
   > ⚠️ **Installiere KEINEN NVIDIA-Linux-Treiber in WSL.** Der Windows-Treiber wird
   > automatisch in WSL eingeblendet. Ein zusätzlicher Linux-Treiber bricht das.
4. **~60 GB frei** auf C: (Modell 23 GB, optional 2. Modell 7 GB, WSL, Docker, node_modules;
   für das llama.cpp-Profil weitere ~25 GB).
5. Empfohlen: **Windows Terminal** (Microsoft Store).
6. Für lange Läufe: *Einstellungen → System → Energie* → Energiesparmodus bei Netzbetrieb
   auf **Nie** (sonst pausiert der Loop, wenn Windows schlafen geht).

## 1. WSL2 + Ubuntu installieren

PowerShell **als Administrator**:

```powershell
wsl --install -d Ubuntu-24.04
```

Neu starten. Ubuntu fragt nach Linux-Benutzername und Passwort (unabhängig von Windows).

```powershell
wsl -l -v          # Ubuntu-24.04 muss VERSION 2 haben
wsl --update       # aktuellen WSL-Kernel holen
```

Bei `VERSION 1`: `wsl --set-version Ubuntu-24.04 2`. Bei Fehlern wie `REGDB_E_CLASSNOTREG`:
Windows-Updates einspielen, unter „Windows-Features“ **Windows-Subsystem für Linux** und
**Plattform für virtuelle Computer** aktivieren, neu starten.

### 1.1 WSL-Ressourcen (`.wslconfig`)

Datei `C:\Users\<DEIN_NAME>\.wslconfig` anlegen:

```ini
[wsl2]
memory=24GB
swap=16GB

[experimental]
autoMemoryReclaim=dropcache
sparseVhd=true
```

- `memory=24GB`: Das Standardmodell liegt zu ~11 GB im RAM, dazu kommen Postgres, Node-Builds
  und OpenCode. 8 GB bleiben für Windows. Wird es in WSL eng, auf `26GB` erhöhen.
- **Kein `processors`-Limit** (anders als vorher): Der CPU-Anteil des Modells profitiert von
  allen Kernen.
- `swap=16GB` fängt Spitzen ab, statt dass Prozesse beendet werden.

Danach in PowerShell `wsl --shutdown` und Ubuntu neu öffnen. (Der VRAM ist davon unabhängig.)

## 2. Ab hier alles im Ubuntu-Terminal (WSL)

### 2.1 Systempakete

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl wget git unzip zstd ca-certificates \
  gnupg jq sqlite3 tmux openssl python3 python3-pip python3-venv
```

`zstd` braucht der Ollama-Installer; `tmux` hält lange Läufe am Leben, wenn du das Terminal schließt.

### 2.2 systemd aktivieren

Nötig für Ollama, Docker und Tailscale als Dienste:

```bash
sudo tee /etc/wsl.conf > /dev/null << 'EOF'
[boot]
systemd=true
EOF
```

In **PowerShell** `wsl --shutdown`, Ubuntu neu öffnen, dann prüfen:

```bash
systemctl is-system-running    # "running" oder "degraded" ist ok
```

## 3. Git einrichten

```bash
git config --global user.name  "Dein Name"
git config --global user.email "deine@email.de"
git config --global init.defaultBranch main
git config --global pull.rebase false
git config --global core.autocrlf input
```

Name und E-Mail sind Pflicht – der Autopilot committet jede erledigte Task.

### 3.1 SSH-Key (nur für Push zu GitHub/GitLab)

```bash
ssh-keygen -t ed25519 -C "deine@email.de"
eval "$(ssh-agent -s)" && ssh-add ~/.ssh/id_ed25519
cat ~/.ssh/id_ed25519.pub     # bei GitHub: Settings → SSH and GPG keys → New SSH key
ssh -T git@github.com
```

## 4. GPU-Zugriff in WSL prüfen

```bash
nvidia-smi
```

Die RTX 4070 Ti muss mit Treiber- und CUDA-Version erscheinen. Falls nicht: Windows-Treiber
aktualisieren, `wsl --update`, `wsl --shutdown`. Für Ollama ist **kein** CUDA-Toolkit in WSL nötig.

## 5. Projekt ins WSL-Dateisystem legen

> ⚠️ **Nicht unter `/mnt/c/...` ablegen** – git, npm und Builds sind dort um ein Vielfaches langsamer.

```bash
mkdir -p ~/projects
cp /mnt/c/Users/<DEIN_NAME>/Downloads/Badminton_IHL.zip ~/projects/
cd ~/projects && unzip Badminton_IHL.zip && cd Badminton_IHL
```

Aus Windows erreichst du die Dateien über `\\wsl.localhost\Ubuntu-24.04\home\<user>\projects`.

### 5.1 Git-Repo initialisieren

```bash
git init
git add .
git commit -m "chore: agent setup"
```

Optional Remote: `git remote add origin git@github.com:<user>/badminton-liga.git && git push -u origin main`

## 6. Ollama installieren und konfigurieren

**Erst nach bestandenem GPU-Check (Abschnitt 4):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama --version
```

Qwen3.6 braucht eine aktuelle Ollama-Version; den Installer erneut auszuführen aktualisiert Ollama.

### 6.1 Server-Einstellungen (wichtig: Kontextfenster)

Ollama nutzt bei weniger als 24 GB VRAM standardmäßig nur **4k** Kontext. Für Agenten und
Coding-Tools empfiehlt Ollama mindestens 64k – sonst werden Prompts abgeschnitten und das Modell
wirkt „vergesslich“. Die fertige Konfiguration liegt im Repo:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo cp scripts/ollama-override.conf /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload && sudo systemctl restart ollama
systemctl show ollama -p Environment      # Kontrolle
```

Inhalt: 64k Kontext, Flash-Attention, quantisierter KV-Cache (q8_0), nur ein Modell und eine
parallele Anfrage (jede weitere würde zusätzlichen KV-Cache reservieren), Modell bleibt 30 min
geladen (zwischen Coder-Schritten laufen `npm install`, Tests und Build).

### 6.2 Modell laden

```bash
ollama pull qwen3.6:35b        # Standard, ~23 GB
ollama pull qwen3.5:9b         # optional: Leicht-Profil, ~6,6 GB
```

### 6.3 Prüfen

```bash
ollama show qwen3.6:35b                                  # unter "Capabilities" muss "tools" stehen
ollama run --think=false qwen3.6:35b "Antworte nur mit: ok"
ollama ps
```

Bei `ollama ps` ist für das 35B-Modell eine Aufteilung wie `45%/55% CPU/GPU` **normal**. Die
Spalte `CONTEXT` muss `65536` zeigen. Beim Leicht-Profil sollte `100% GPU` stehen.

## 7. Node.js und OpenCode

### 7.1 Node.js 22 LTS

Node.js ist **Pflicht**: Die Agenten bauen eine Next.js-App (Next.js 16 braucht Node ≥ 20.9,
Vitest 5 die Typen für Node ≥ 22).

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
source ~/.bashrc
nvm install 22 && nvm alias default 22
node -v && npm -v
```

### 7.2 OpenCode (Version 1.18.x, fest eingestellt)

```bash
npm install -g opencode-ai@1.18.33
opencode --version
```

**Warum nicht OpenCode 2?** OpenCode 2.0 ist erschienen, aber noch jung: In 2.0.12 werden die
neuen `permissions:` in Markdown-Agenten nicht angewendet, Language Server laufen nicht, und
Temperaturwerte pro Agent werden nicht gesendet. Die Konfiguration hier nutzt das V1-Format,
das V2 ebenfalls liest – ein späterer Umstieg bleibt möglich. Für einen autonomen Loop zählt
Stabilität. `"autoupdate": false` in `opencode.json` verhindert ungewollte Updates.

### 7.3 Konfiguration (liegt im Repo)

- `opencode.json`: Provider `ollama` (Standard) und `llamacpp` (optional), Kontextgrenzen
  passend zu Ollama (65 536 Token), ein Modell für alle Rollen inkl. `small_model` (für
  Session-Titel – sonst würde dafür ein zweites Modell geladen), Web-Zugriff aus.
- `AGENTS.md`: Projektkontext und harte Regeln für alle Agenten (wird in jeden Prompt geladen,
  daher kurz gehalten).
- `.opencode/agents/*.md`: Rollen `planner`, `coder`, `spec-reviewer`, `quality-reviewer` mit
  eng gesetzten Rechten. Beispiel: Der Coder darf `TASKS.md`, `scripts/` oder `docs/` nicht
  ändern und kein `git commit`/`push` ausführen; Reviewer dürfen nichts ändern.

Lokales Ollama braucht **keinen API-Key**.

## 8. Docker (Dev-Datenbank, später Hosting)

Empfohlen: **Docker Engine direkt in WSL** (braucht systemd aus 2.2, spart gegenüber Docker
Desktop RAM):

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Terminal schließen und neu öffnen, dann:
docker run --rm hello-world
```

Alternative: Docker Desktop unter Windows mit *Settings → Resources → WSL integration →
Ubuntu-24.04*. Das NVIDIA Container Toolkit brauchst du nicht.

## 9. Web-Grundgerüst und Dev-Datenbank

Das Next.js-Grundgerüst wird **per Skript** erzeugt statt vom Modell. Das ist der
fehleranfälligste Schritt (interaktive Generatoren, Versionskonflikte) und bringt dem Modell
nichts. Das Skript ist durchgetestet (Typecheck, Lint, Test und Build grün).

```bash
cd ~/projects/Badminton_IHL
docker compose -f compose.dev.yml up -d        # Postgres 17 + Mailpit (nur auf 127.0.0.1)
bash scripts/bootstrap-web.sh                  # dauert einige Minuten
git add -A && git commit -m "T001: Web-Grundgerüst (bootstrap)"
```

Das Skript legt `web/` an (Next.js 16, TypeScript, Tailwind 4, Drizzle + pg, Better Auth, Zod,
Vitest), setzt die npm-Skripte, erzeugt `web/.env` mit zufälligem Auth-Secret, führt
`scripts/check.sh` aus und setzt T001 in `TASKS.md` auf `done`.

## 10. Autopilot (autonomer Loop)

### 10.1 Einmalig einrichten

```bash
cd ~/projects/Badminton_IHL
python3 -m venv autopilot/.venv
source autopilot/.venv/bin/activate
pip install -r autopilot/requirements.txt
cp autopilot/.env.example autopilot/.env
python -m pytest -q autopilot/tests            # 19 Tests, alle grün
bash scripts/verify-setup.sh --warmup          # Gesamtcheck inkl. Modell-Aufwärmen
```

### 10.2 Erster Lauf – Schritt für Schritt

```bash
python autopilot/run.py --dry-run     # zeigt nächste Task + Arbeitsauftrag, ändert nichts
python autopilot/run.py --once        # genau eine Task
git log --oneline -3 && git show --stat HEAD
```

### 10.3 Dauerlauf

```bash
tmux new -s liga                       # Sitzung überlebt geschlossene Terminals
source autopilot/.venv/bin/activate
python autopilot/run.py                # läuft, bis nichts mehr offen ist
# abkoppeln: Strg+B, dann D   ·   wieder verbinden: tmux attach -t liga
```

Weitere Optionen: `--task T007` (gezielt eine Task), `--skip-brief` (ohne Planner-Schritt),
`--max-tasks 5`. Einstellungen in `autopilot/.env` (Versuche pro Task, Zeitlimits, Build an/aus).

Der Lauf stoppt von selbst, wenn nichts mehr offen ist oder zwei Tasks hintereinander blockiert
wurden. Protokolle je Task (inkl. Prompts, Coder-Bericht, Check-Ausgabe, Reviews): `.autopilot/logs/`.

### 10.4 Nach dem Lauf

1. `git log --oneline` – jede erledigte Task ist ein Commit; nicht blockierende Hinweise des
   Quality-Reviewers stehen im Commit-Text.
2. Diffs stichprobenartig ansehen (`git show <commit>`).
3. **UI-Tasks selbst ansehen** (Definition of Done, Punkt 4 – kann der Autopilot nicht):
   `cd web && npm run dev`, im Windows-Browser `http://localhost:3000` öffnen und in den
   Entwicklertools die Gerätesimulation auf ~375 px stellen.

### 10.5 Blockierte Tasks

Eine blockierte Task steht in `TASKS.md` mit `status: blocked` und einer `> BLOCKED:`-Zeile
(Grund, Pfad zu Log und gesichertem Patch). Möglichkeiten:

- **Task schärfen:** Beschreibung oder Akzeptanzkriterien präzisieren oder die Task teilen,
  `status: open` setzen, `> BLOCKED`-Zeile löschen, committen, neu starten.
- **Letzten Versuch weiterverwenden:** `git apply .autopilot/blocked/<datei>.patch`, von Hand
  oder im interaktiven Modus fertigstellen, committen, Status auf `done`.
- **Offene Fachfragen** (T090–T092): Frage in `docs/PROJECT_SPEC.md` Abschnitt 11 beantworten,
  Task beschreiben und auf `open` setzen.

## 11. Interaktiver Modus (OpenCode-Oberfläche)

```bash
cd ~/projects/Badminton_IHL
opencode
```

- Start-Agent ist `planner`. `/models` zeigt die Modelle, `Tab` wechselt zwischen
  Primär-Agenten, mit `@coder …` sprichst du den Coder direkt an.
- Erster Test: *„Lies TASKS.md und schlage die nächste Task vor. Ändere noch nichts.“*
- Der Planner delegiert selbst an Coder und Reviewer. Mit lokalen Modellen ist das weniger
  verlässlich als der Autopilot – gut zum Zuschauen, Nachbessern und für knifflige Tasks.
  Committen musst du im interaktiven Modus selbst.

## 12. Setup-Check

```bash
bash scripts/verify-setup.sh            # schnell
bash scripts/verify-setup.sh --warmup   # zusätzlich Modell laden und GPU/CPU-Verteilung zeigen
```

Prüft WSL, systemd, RAM, Tools, Node- und OpenCode-Version, Docker, Git, GPU,
Ollama-Konfiguration, Modell samt Tool-Support und die Projektdateien.

## 13. Zugriff unterwegs per Tailscale (laut Spec: nur VPN)

Relevant, sobald die App produktiv läuft (Task T031). WSL2 liegt hinter einem NAT, daher
Tailscale **in WSL** installieren (braucht systemd aus 2.2):

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

Auf den Handys die Tailscale-App installieren und demselben Tailnet beitreten. Aufruf über
`http://<tailnet-ip>:<port>` oder den MagicDNS-Namen; Dienste im Container müssen an `0.0.0.0`
binden. Tailscale nur unter Windows ist fehleranfälliger (Portweiterleitung). Ungetestet auf
deiner Maschine – am Ende vom Handy mit mobilen Daten (WLAN aus) prüfen.

## 14. Optional: VS Code

VS Code unter Windows + Erweiterung **WSL**; `code .` im Projektordner öffnet das Projekt direkt in WSL.

## 15. Discord-Benachrichtigungen (später)

Noch nicht Teil dieses Repos. Ansatzpunkte: `autopilot/nodes/finalize.py` (nach Commit oder
Block eine Webhook-Nachricht senden) bzw. `interrupt()` in LangGraph für Freigaben per Chat.

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| `nvidia-smi` fehlt in WSL | Windows-Treiber aktualisieren, `wsl --update`, `wsl --shutdown`; keinen Linux-Treiber installieren |
| `ollama ps` zeigt `100% CPU` | GPU-Check (Abschnitt 4) bestehen, Ollama-Installer erneut ausführen |
| `CONTEXT` in `ollama ps` ist nicht 65536 | Abschnitt 6.1 wiederholen, `systemctl show ollama -p Environment` prüfen |
| Agent „vergisst“ Dinge, bricht Tool-Calls ab | Kontext (s. o.) prüfen; Modell auf Tool-Support prüfen (`ollama show`) |
| Log meldet „Tool-Aufruf als Text ausgegeben“ | Bekanntes Template-/Parser-Problem einiger Ollama-Versionen mit Qwen-Modellen: Ollama aktualisieren; hilft das nicht, llama.cpp-Profil (Anhang A) nutzen |
| Autopilot: „Arbeitsverzeichnis nicht sauber“ | `git status`; committen oder `git reset --hard HEAD && git clean -fd` |
| Autopilot: „LLM-Endpunkt … nicht erreichbar“ | `systemctl status ollama`; Modellname in `autopilot/.env` muss exakt `ollama list` entsprechen |
| WSL wird langsam, Prozesse werden beendet | RAM: Browser-Tabs in Windows schließen, `.wslconfig` `memory=26GB`, oder Leicht-Profil |
| `check.sh`: Build rot, Typecheck grün | Oft Server-/Client-Komponenten-Fehler – das Feedback geht automatisch an den Coder; schneller iterieren mit `CHECK_BUILD=0` in `autopilot/.env` |
| Migration hängt | `drizzle-kit generate` fragt bei vermuteten Umbenennungen interaktiv nach. Umbenennungen in eigene Schritte teilen (erst neue Spalte, dann alte entfernen) |
| Dev-DB kaputt nach Experimenten | `bash scripts/reset-dev-db.sh` (setzt auf die committeten Migrationen zurück) |
| `systemctl`: „System has not been booted with systemd“ | Abschnitt 2.2, dann `wsl --shutdown` |
| Sehr langsame git-/npm-Befehle | Projekt liegt unter `/mnt/c` → nach `~/projects` verschieben |

---

## Anhang A – Performance-Profil mit llama.cpp (optional)

Ollama verteilt ein zu großes Modell schichtweise auf GPU und CPU. llama.cpp kann gezielt nur
die MoE-Experten in den RAM legen (`--n-cpu-moe`), während Attention und KV-Cache auf der GPU
bleiben – bei MoE-Modellen auf kleinen GPUs meist spürbar schneller. **Nicht auf deiner
Maschine getestet**, daher optional.

```bash
# CUDA-Toolkit aus dem WSL-spezifischen NVIDIA-Repo (enthält KEINEN Treiber – richtig so)
wget https://developer.download.nvidia.com/compute/cuda/repos/wsl-ubuntu/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb && sudo apt update
sudo apt install -y cuda-toolkit cmake libcurl4-openssl-dev libssl-dev
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc && source ~/.bashrc

git clone https://github.com/ggml-org/llama.cpp ~/llama.cpp && cd ~/llama.cpp
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89     # 89 = RTX 40xx
cmake --build build --config Release -j 16
```

Starten (lädt das Modell beim ersten Mal von Hugging Face, ~22 GB):

```bash
sudo systemctl stop ollama          # beide Server passen nicht gleichzeitig in 12 GB
cd ~/projects/Badminton_IHL && bash scripts/llama-server.sh
```

Tuning: `N_CPU_MOE` (Start 28 von 40 Schichten) senken, solange `nvidia-smi` noch VRAM frei
zeigt; bei „out of memory“ erhöhen. Dann umstellen:

- `autopilot/.env`: `LLM_BASE_URL=http://localhost:8080/v1`, `LLM_MODEL=qwen3.6-35b-a3b`,
  `OPENCODE_MODEL=llamacpp/qwen3.6-35b-a3b`
- `opencode.json` (nur für den interaktiven Modus): `model` und `small_model` auf
  `llamacpp/qwen3.6-35b-a3b`

## Anhang B – Modell wechseln

Das Modell steht an genau zwei Stellen und muss dort übereinstimmen:

1. `autopilot/.env`: `LLM_MODEL` und `OPENCODE_MODEL`
2. `opencode.json`: `model` und `small_model` (interaktiver Modus)

Neue Ollama-Modelle zusätzlich unter `provider.ollama.models` eintragen (mit
`limit.context` = 65536). Voraussetzung: `ollama show <modell>` listet `tools`.

---

## Ordnerstruktur

```
Badminton_IHL/
├── README.md                     diese Anleitung
├── AGENTS.md                     Projektregeln für alle Agenten
├── TASKS.md                      Task-Board (maschinenlesbar)
├── opencode.json                 Provider, Modell, globale Rechte
├── compose.dev.yml               Postgres + Mailpit für die Entwicklung
├── .opencode/agents/             planner, coder, spec-reviewer, quality-reviewer
├── docs/
│   ├── PROJECT_SPEC.md           fachliche Spezifikation
│   └── CHANGES.md                Änderungen gegenüber der Vorversion und warum
├── scripts/
│   ├── bootstrap-web.sh          erzeugt web/ (Task T001)
│   ├── check.sh                  Prüf-Gate: typecheck, lint, test, build
│   ├── verify-setup.sh           Umgebungs-Check
│   ├── ollama-override.conf      systemd-Konfiguration für Ollama
│   ├── reset-dev-db.sh           Dev-DB auf committete Migrationen zurücksetzen
│   └── llama-server.sh           optionales Performance-Profil
├── autopilot/                    autonomer Loop (Python + LangGraph)
│   ├── run.py                    Einstieg
│   ├── graph.py · state.py       Ablauf
│   ├── nodes/                    select_task, planner, coder, checks, reviewers, finalize
│   ├── tasks.py · gitutil.py · checks.py · llm.py · opencode_runner.py · context.py
│   ├── prompts/brief.md          Prompt für den Planner-Schritt
│   └── tests/                    Unit-Tests
└── web/                          Next.js-App (entsteht durch bootstrap-web.sh)
```
