"""
Autopilot für den autonomen Loop:  Task wählen → Arbeitsauftrag → Coder (OpenCode) → Checks
→ Spec-Review → Quality-Review → Commit  (oder nach MAX_REVISIONS: Rollback + blocked).

Beispiele (aus dem Repo-Root, venv aktiv):
  python autopilot/run.py --dry-run          # nur nächste Task + Arbeitsauftrag anzeigen
  python autopilot/run.py --once             # genau eine Task
  python autopilot/run.py --task T007        # gezielt eine Task
  python autopilot/run.py                    # Dauerlauf, bis nichts mehr offen ist
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gitutil  # noqa: E402
import llm  # noqa: E402
import tasks  # noqa: E402
from config import REPO_ROOT, SETTINGS  # noqa: E402
from graph import build_graph  # noqa: E402
from nodes.common import say  # noqa: E402


def preflight(dry_run: bool) -> list[str]:
    problems: list[str] = []
    try:
        gitutil.head()
    except gitutil.GitError:
        return ["Kein Git-Repo mit mindestens einem Commit (README Abschnitt 5.1)."]
    if not gitutil.has_identity():
        problems.append("git user.email ist nicht gesetzt (README Abschnitt 3).")
    if not dry_run and not gitutil.is_clean():
        problems.append("Arbeitsverzeichnis nicht sauber. Erst committen oder verwerfen (git status).")
    if not (REPO_ROOT / "web" / "package.json").exists():
        problems.append("web/ fehlt – zuerst `bash scripts/bootstrap-web.sh` ausführen (README Abschnitt 9).")
    else:
        t001 = next((t for t in tasks.load() if t.id == "T001"), None)
        if t001 and t001.status == "open":
            tasks.set_status("T001", "done")
            say("T001 war noch offen, web/ existiert aber – auf done gesetzt (bitte committen).")
            if not dry_run:
                problems.append("TASKS.md wurde angepasst (T001 → done). Bitte committen und neu starten.")
    ok, detail = llm.ping()
    if not ok:
        problems.append(f"LLM-Endpunkt: {detail}")
    if shutil.which(SETTINGS.opencode_bin) is None:
        problems.append(f"OpenCode nicht gefunden ({SETTINGS.opencode_bin}).")
    else:
        v = subprocess.run([SETTINGS.opencode_bin, "--version"], capture_output=True, text=True).stdout.strip()
        if v and not v.startswith("1."):
            say(f"Hinweis: OpenCode {v} – getestet ist 1.18.x (siehe README 7.2).")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="nur eine Task bearbeiten")
    ap.add_argument("--task", help="gezielt diese Task-ID bearbeiten (muss open sein)")
    ap.add_argument("--max-tasks", type=int, default=100, help="Obergrenze Tasks pro Lauf")
    ap.add_argument("--dry-run", action="store_true", help="nur Auswahl + Arbeitsauftrag, nichts ändern")
    ap.add_argument("--skip-brief", action="store_true", help="Planner-Schritt überspringen (Task-Text direkt)")
    ap.add_argument("--skip-preflight", action="store_true")
    args = ap.parse_args()

    if not args.skip_preflight:
        problems = preflight(args.dry_run)
        if problems:
            print("Vorabprüfung fehlgeschlagen:\n- " + "\n- ".join(problems))
            return 2

    say(f"Autopilot: Modell {SETTINGS.llm_model} | Coder {SETTINGS.opencode_model} | "
        f"max. {SETTINGS.max_revisions} Versuche/Task")
    app = build_graph()
    done = blocked = blocked_in_row = 0
    started = time.time()
    try:
        for _ in range(args.max_tasks):
            state = app.invoke({"only_task": args.task, "dry_run": args.dry_run, "skip_brief": args.skip_brief},
                               config={"recursion_limit": 200})
            if state.get("no_task"):
                break
            if args.dry_run:
                print("\n" + "=" * 70 + "\n" + state.get("work_order", "") + "\n" + "=" * 70)
                print(f"Log: {state.get('log_path')}")
                break
            if state.get("outcome") == "done":
                done += 1
                blocked_in_row = 0
            else:
                blocked += 1
                blocked_in_row += 1
                if blocked_in_row >= SETTINGS.max_blocked_in_row:
                    say(f"{blocked_in_row} Tasks hintereinander blockiert – Lauf wird angehalten. "
                        "Bitte .autopilot/logs ansehen.")
                    break
            if args.once or args.task:
                break
    except KeyboardInterrupt:
        print("\nAbgebrochen. Das Arbeitsverzeichnis kann halbfertige Änderungen enthalten:\n"
              "  git status            # ansehen\n"
              "  git reset --hard HEAD && git clean -fd   # verwerfen")
        return 130
    mins = int((time.time() - started) / 60)
    say(f"Lauf beendet nach {mins} min: {done} erledigt, {blocked} blockiert.")
    return 0 if blocked == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
