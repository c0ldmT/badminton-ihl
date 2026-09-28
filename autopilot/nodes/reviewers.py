"""Spec- und Quality-Review: bekommen den echten Diff + Check-Ergebnis, nicht nur den Coder-Bericht."""
from __future__ import annotations

import context
import gitutil
import llm
from config import SETTINGS
from nodes.common import fail, log, ok, say

JSON_SUFFIX = ("\n\nWICHTIG: Deine Antwort besteht ausschließlich aus dem JSON-Objekt im oben "
               "beschriebenen Format – kein weiterer Text.")


def _review_input(state: dict) -> str:
    return (
        f"# Task\n{state['task_block']}\n\n"
        f"# Arbeitsauftrag\n{state.get('work_order', '')}\n\n"
        f"# Ergebnis der automatischen Checks (scripts/check.sh)\n{state.get('check_summary', '')}\n\n"
        f"# Bericht des Coders (nur Behauptung, am Diff überprüfen!)\n{state.get('coder_report', '')[:3000]}\n\n"
        f"# Diff seit Task-Beginn\n{gitutil.diff_for_review(state['base_commit'], SETTINGS.review_diff_chars)}\n"
    )


def _review(state: dict, role: str, gate: str) -> tuple[dict, llm.Verdict]:
    say(f"  {role} …")
    try:
        answer = llm.chat(context.agent_prompt(role) + JSON_SUFFIX, _review_input(state))
        verdict = llm.parse_verdict(answer)
    except llm.LLMError as e:
        answer = str(e)
        verdict = llm.Verdict("FAIL", "Review-Aufruf fehlgeschlagen", [str(e)], parsed=False)
    log(state, role, f"Urteil: {verdict.verdict}\n\n{answer}")
    if verdict.passed:
        return ok(gate), verdict
    return fail(state, gate, f"{role} sagt FAIL:\n{verdict.as_feedback()}"), verdict


def spec_review_node(state: dict) -> dict:
    upd, v = _review(state, "spec-reviewer", "spec")
    return {**upd, "spec_summary": v.summary}


def quality_review_node(state: dict) -> dict:
    upd, v = _review(state, "quality-reviewer", "quality")
    return {**upd, "quality_summary": v.summary, "quality_hints": v.hints}
