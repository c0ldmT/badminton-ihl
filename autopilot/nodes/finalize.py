from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path

import gitutil
import tasks
from config import PATCH_DIR, REPO_ROOT, SETTINGS
from nodes.common import log, say


def _rel(path: str) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except ValueError:
        return path


def done_node(state: dict) -> dict:
    tasks.set_status(state["task_id"], "done")
    hints = state.get("quality_hints") or []
    msg = f"{state['task_id']}: {state['task_title']}\n\nautopilot: checks+spec+quality PASS"
    if hints:
        msg += "\n\nHinweise (nicht blockierend):\n" + "\n".join(f"- {h}" for h in hints[:10])
    sha = gitutil.commit(msg)
    say(f"✔ {state['task_id']} erledigt – Commit {sha[:8]}")
    log(state, "Ergebnis", f"DONE, Commit {sha}")
    return {"outcome": "done", "commit": sha}


def blocked_node(state: dict) -> dict:
    base = state["base_commit"]
    files = gitutil.changed_files(base)
    patch = PATCH_DIR / f"{state['task_id']}_{dt.datetime.now():%Y%m%d-%H%M%S}.patch"
    gitutil.save_patch(base, patch)
    gitutil.rollback(base)
    touched_db = any(f.startswith("web/drizzle/") or "/db/schema" in f for f in files)
    if touched_db and SETTINGS.reset_db_on_rollback:
        r = subprocess.run(["bash", "scripts/reset-dev-db.sh"], cwd=REPO_ROOT, capture_output=True, text=True)
        log(state, "Dev-DB zurückgesetzt", (r.stdout + r.stderr)[-2000:])
    reason = (f"Autopilot: {SETTINGS.max_revisions} Fehlversuche, zuletzt am Gate '{state.get('last_gate')}'. "
              f"Patch: .autopilot/blocked/{patch.name}. Log: {_rel(state.get('log_path', ''))}")
    tasks.set_status(state["task_id"], "blocked", reason)
    sha = gitutil.commit(f"chore(tasks): {state['task_id']} blocked")
    say(f"■ {state['task_id']} blockiert – Änderungen verworfen, Patch gesichert ({patch.name})")
    log(state, "Ergebnis", f"BLOCKED\n\n{reason}\n\nLetztes Feedback:\n{state.get('feedback', '')}")
    return {"outcome": "blocked", "reason": reason, "commit": sha}
