"""Zustand eines Task-Durchlaufs durch den Graphen."""
from __future__ import annotations

from typing import TypedDict


class TaskState(TypedDict, total=False):
    # Steuerung
    only_task: str            # --task
    dry_run: bool
    skip_brief: bool
    no_task: bool             # keine passende Task gefunden -> Ende
    # Task
    task_id: str
    task_title: str
    task_block: str
    spec_refs: list[str]
    base_commit: str
    log_path: str
    work_order: str
    # Revisionen
    revision: int             # Anzahl bisheriger FEHLversuche
    feedback: str             # Feedback für den nächsten Coder-Versuch
    last_gate: str            # coder | checks | spec | quality
    gate_passed: bool
    # Ergebnisse
    coder_report: str
    check_summary: str
    spec_summary: str
    quality_summary: str
    quality_hints: list[str]
    outcome: str              # done | blocked | dry_run
    reason: str
    commit: str
