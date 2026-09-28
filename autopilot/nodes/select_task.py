from __future__ import annotations

import datetime as dt

import gitutil
import tasks
from config import LOG_DIR
from nodes.common import ensure_parent, say


def select_task_node(state: dict) -> dict:
    t = tasks.next_task(tasks.load(), state.get("only_task"))
    if t is None:
        say("Keine offene Task mit erfüllten Abhängigkeiten – fertig.")
        return {"no_task": True}
    log_path = ensure_parent(LOG_DIR / f"{dt.datetime.now():%Y%m%d-%H%M%S}_{t.id}.md")
    log_path.write_text(f"# {t.label}\n\n```\n{t.block}\n```\n", encoding="utf-8")
    say(f"▶ {t.label}")
    return {
        "no_task": False, "task_id": t.id, "task_title": t.title, "task_block": t.block,
        "spec_refs": t.spec, "base_commit": gitutil.head(), "log_path": str(log_path),
        "revision": 0, "feedback": "", "work_order": "",
    }
