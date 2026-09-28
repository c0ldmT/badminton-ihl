"""Coder-Schritt: OpenCode-Agent `coder` setzt den Auftrag mit echten Datei-/Shell-Tools um."""
from __future__ import annotations

import gitutil
from config import SETTINGS
from nodes.common import fail, log, ok, say
from opencode_runner import run_coder

RULES = """## Regeln für diesen Lauf
- Nur diese Task. Keine git-Commits (macht der Autopilot). Kein Dev-Server, kein Watch-Modus.
- Nicht ändern: TASKS.md, AGENTS.md, docs/, scripts/, autopilot/, .opencode/, opencode.json, compose.dev.yml.
- Zum Schluss `bash scripts/check.sh` ausführen und Fehler beheben.
- Letzte Nachricht: kurzer Abschlussbericht (GEÄNDERT / ERGEBNIS check.sh / OFFEN)."""


def build_prompt(state: dict) -> str:
    attempt = state.get("revision", 0) + 1
    parts = [f"# Auftrag {state['task_id']}: {state['task_title']} (Versuch {attempt}/{SETTINGS.max_revisions})",
             f"## Arbeitsauftrag\n{state.get('work_order') or state['task_block']}",
             f"## Task-Definition (TASKS.md)\n{state['task_block']}"]
    if state.get("feedback"):
        parts.append("## Feedback aus dem letzten Versuch – MUSS behoben werden\n"
                     f"{state['feedback']}\n\n"
                     "Der bisherige Stand des letzten Versuchs ist noch im Arbeitsverzeichnis. "
                     "Baue darauf auf, statt von vorn zu beginnen.\n\n"
                     f"Bisher geänderte Dateien:\n```\n{gitutil.diff_stat(state['base_commit'])}\n```")
    parts.append(RULES)
    return "\n\n".join(parts)


def coder_node(state: dict) -> dict:
    say(f"  Coder arbeitet (Versuch {state.get('revision', 0) + 1}) …")
    prompt = build_prompt(state)
    log(state, f"Coder-Prompt {state.get('revision', 0) + 1}", prompt)
    res = run_coder(prompt, title=f"{state['task_id']} Versuch {state.get('revision', 0) + 1}")
    log(state, f"Coder-Versuch {state.get('revision', 0) + 1}",
        f"Dauer {res.seconds}s, Tool-Aufrufe {res.tool_calls} (Fehler {res.tool_errors})\n\n"
        f"Problem: {res.problem or '-'}\n\n### Bericht\n{res.final_text or '(leer)'}\n\n"
        "### Letzte Ausgabezeilen\n```\n" + "\n".join(res.raw_tail[-15:]) + "\n```")

    protected = gitutil.protected_changes(state["base_commit"])
    if protected:
        gitutil.restore_paths(state["base_commit"], protected)
        log(state, "Geschützte Dateien zurückgesetzt", "\n".join(protected))

    if res.problem:
        return {**fail(state, "coder", f"Der letzte Coder-Lauf ist gescheitert: {res.problem}. "
                                        "Nutze die Tools (read/edit/write/bash) direkt, nicht als Text."),
                "coder_report": res.final_text}
    if not gitutil.changed_files(state["base_commit"]):
        return {**fail(state, "coder", "Es wurden keine Dateien geändert. Setze die Task tatsächlich um."),
                "coder_report": res.final_text}
    extra = f"\n\nHinweis: Änderungen an geschützten Dateien wurden verworfen: {', '.join(protected)}" if protected else ""
    return {**ok("coder"), "coder_report": (res.final_text or "") + extra}
