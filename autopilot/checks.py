"""Führt scripts/check.sh aus – das objektive Prüf-Gate vor jedem LLM-Review."""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

from config import REPO_ROOT, SETTINGS


@dataclass
class CheckResult:
    ok: bool
    summary: str       # nur die "=== step: OK/FEHLGESCHLAGEN"-Zeilen
    output: str        # gekürzte Gesamtausgabe für Coder-Feedback


def run_checks() -> CheckResult:
    env = {**os.environ, "CHECK_BUILD": SETTINGS.check_build, "CI": "1"}
    try:
        p = subprocess.run(["bash", "scripts/check.sh"], cwd=REPO_ROOT, env=env, capture_output=True,
                           text=True, timeout=SETTINGS.check_timeout_min * 60, stdin=subprocess.DEVNULL)
        out = (p.stdout or "") + (p.stderr or "")
        ok = p.returncode == 0
    except subprocess.TimeoutExpired as e:
        out = f"{e.stdout or ''}\nZEITÜBERSCHREITUNG nach {SETTINGS.check_timeout_min} min"
        ok = False
    summary = "\n".join(line for line in out.splitlines()
                        if line.startswith("=== ") and (line.rstrip().endswith("OK") or "FEHLGESCHLAGEN" in line)
                        or line.startswith("CHECK RESULT"))
    lines = out.splitlines()
    return CheckResult(ok, summary or "(keine Zusammenfassung)", "\n".join(lines[-200:]))
