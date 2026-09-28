from __future__ import annotations

import datetime as dt
from pathlib import Path

from config import SETTINGS


def log(state: dict, heading: str, body: str) -> None:
    path = state.get("log_path")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n\n## {heading}  ({dt.datetime.now():%H:%M:%S})\n\n{body.strip()}\n")


def say(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def fail(state: dict, gate: str, feedback: str) -> dict:
    """Einheitliche Behandlung eines nicht bestandenen Gates."""
    rev = state.get("revision", 0) + 1
    say(f"  ✗ {gate} nicht bestanden (Fehlversuch {rev}/{SETTINGS.max_revisions})")
    return {"revision": rev, "feedback": feedback, "last_gate": gate, "gate_passed": False}


def ok(gate: str) -> dict:
    say(f"  ✓ {gate}")
    return {"last_gate": gate, "gate_passed": True}


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
