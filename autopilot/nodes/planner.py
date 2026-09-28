"""Planner-Schritt: verfeinert die gewählte Task zu einem Arbeitsauftrag (wählt NICHT aus)."""
from __future__ import annotations

import context
import llm
from config import AGENTS_PATH
from nodes.common import log, say


def brief_node(state: dict) -> dict:
    if state.get("skip_brief"):
        return {"work_order": state["task_block"]}
    say("  Planner erstellt Arbeitsauftrag …")
    user = (
        f"# Task\n{state['task_block']}\n\n"
        f"# Projektregeln (AGENTS.md)\n{AGENTS_PATH.read_text(encoding='utf-8')}\n\n"
        f"# Relevante Spec-Abschnitte\n{context.spec_sections(state.get('spec_refs', []))}\n\n"
        f"# Dateien im Repo (git ls-files)\n{context.repo_overview()}\n"
    )
    try:
        order = llm.chat(context.local_prompt("brief"), user, max_tokens=8000)
    except llm.LLMError as e:
        say(f"  Planner fehlgeschlagen ({e}) – nutze Task-Text direkt.")
        order = state["task_block"]
    log(state, "Arbeitsauftrag (Planner)", order)
    return {"work_order": order}
