"""
Ein Graph-Durchlauf = eine Task. Der Ablauf ist deterministisch (Code), die LLMs erledigen
nur klar begrenzte Einzelschritte mit jeweils frischem Kontext.

  select_task ─(keine Task)─► END
      │
    brief (Planner verfeinert) ─(dry-run)─► END
      │
    coder ──► checks ──► spec_review ──► quality_review ──► done ──► END
      ▲         │FAIL        │FAIL            │FAIL
      └─────────┴────────────┴────────────────┘   (bis MAX_REVISIONS, dann ► blocked ► END)
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from config import SETTINGS
from nodes.checks import checks_node
from nodes.coder import coder_node
from nodes.finalize import blocked_node, done_node
from nodes.planner import brief_node
from nodes.reviewers import quality_review_node, spec_review_node
from nodes.select_task import select_task_node
from state import TaskState


def route_gate(next_node: str):
    def _route(state: TaskState) -> str:
        if state.get("gate_passed"):
            return next_node
        if state.get("revision", 0) >= SETTINGS.max_revisions:
            return "blocked"
        return "coder"
    return _route


def route_after_select(state: TaskState) -> str:
    return END if state.get("no_task") else "brief"


def route_after_brief(state: TaskState) -> str:
    return END if state.get("dry_run") else "coder"


def build_graph():
    g = StateGraph(TaskState)
    g.add_node("select_task", select_task_node)
    g.add_node("brief", brief_node)
    g.add_node("coder", coder_node)
    g.add_node("checks", checks_node)
    g.add_node("spec_review", spec_review_node)
    g.add_node("quality_review", quality_review_node)
    g.add_node("done", done_node)
    g.add_node("blocked", blocked_node)

    g.add_edge(START, "select_task")
    g.add_conditional_edges("select_task", route_after_select, {"brief": "brief", END: END})
    g.add_conditional_edges("brief", route_after_brief, {"coder": "coder", END: END})
    g.add_conditional_edges("coder", route_gate("checks"), {"checks": "checks", "coder": "coder", "blocked": "blocked"})
    g.add_conditional_edges("checks", route_gate("spec_review"),
                            {"spec_review": "spec_review", "coder": "coder", "blocked": "blocked"})
    g.add_conditional_edges("spec_review", route_gate("quality_review"),
                            {"quality_review": "quality_review", "coder": "coder", "blocked": "blocked"})
    g.add_conditional_edges("quality_review", route_gate("done"), {"done": "done", "coder": "coder", "blocked": "blocked"})
    g.add_edge("done", END)
    g.add_edge("blocked", END)
    return g.compile()
