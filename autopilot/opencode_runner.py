"""Startet den Coder als `opencode run --agent coder` (nicht-interaktiv, JSON-Events)."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field

from config import REPO_ROOT, SETTINGS

# Typisches Fehlerbild lokaler Modelle: Tool-Call wird als Text ausgegeben statt ausgeführt.
TEXT_TOOLCALL_RE = re.compile(r"<tool_call>|<function=|\{\s*\"name\"\s*:\s*\"(bash|edit|write|read|glob|grep)\"", re.I)


@dataclass
class CoderResult:
    ok: bool
    final_text: str = ""
    tool_calls: int = 0
    tool_errors: int = 0
    seconds: int = 0
    problem: str = ""                      # leer = kein erkanntes Problem
    raw_tail: list[str] = field(default_factory=list)


def parse_events(lines: list[str]) -> tuple[str, int, int]:
    texts: dict[str, list[str]] = {}
    order: list[str] = []
    tools = errors = 0
    for line in lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = ev.get("part") or {}
        if ev.get("type") == "text" and part.get("text"):
            mid = part.get("messageID", "?")
            if mid not in texts:
                texts[mid] = []
                order.append(mid)
            texts[mid].append(part["text"])
        elif ev.get("type") == "tool_use":
            tools += 1
            if (part.get("state") or {}).get("status") == "error":
                errors += 1
    final = "\n".join(texts[order[-1]]) if order else ""
    return final.strip(), tools, errors


def run_coder(prompt: str, title: str) -> CoderResult:
    cmd = [SETTINGS.opencode_bin, "run", "--agent", "coder", "--model", SETTINGS.opencode_model,
           "--format", "json", "--title", title, prompt]
    start = time.time()
    try:
        proc = subprocess.Popen(cmd, cwd=REPO_ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, start_new_session=True)
    except FileNotFoundError:
        return CoderResult(False, problem=f"OpenCode nicht gefunden ({SETTINGS.opencode_bin})")
    try:
        out, _ = proc.communicate(timeout=SETTINGS.coder_timeout_min * 60)
        timed_out = False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            out, _ = proc.communicate(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, _ = proc.communicate()
        timed_out = True
    lines = (out or "").splitlines()
    final, tools, errors = parse_events(lines)
    res = CoderResult(ok=proc.returncode == 0 and not timed_out, final_text=final, tool_calls=tools,
                      tool_errors=errors, seconds=int(time.time() - start), raw_tail=lines[-40:])
    if timed_out:
        res.problem = f"Zeitlimit von {SETTINGS.coder_timeout_min} min überschritten"
    elif proc.returncode != 0:
        res.problem = f"opencode beendete sich mit Code {proc.returncode}"
    elif tools == 0:
        res.problem = "Der Coder hat kein einziges Tool benutzt (keine Datei gelesen oder geändert)"
    elif TEXT_TOOLCALL_RE.search(final):
        res.problem = ("Tool-Aufruf wurde als Text ausgegeben statt ausgeführt (bekanntes Template-/"
                       "Parser-Problem lokaler Modelle)")
    return res
