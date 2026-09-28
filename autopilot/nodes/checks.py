from __future__ import annotations

from checks import run_checks
from nodes.common import fail, log, ok, say


def checks_node(state: dict) -> dict:
    say("  Prüf-Gate scripts/check.sh …")
    r = run_checks()
    log(state, "check.sh", f"{r.summary}\n\n```\n{r.output[-6000:]}\n```")
    if r.ok:
        return {**ok("checks"), "check_summary": r.summary}
    return {**fail(state, "checks", "`bash scripts/check.sh` ist rot. Behebe diese Fehler:\n```\n"
                   f"{r.output[-5000:]}\n```"), "check_summary": r.summary}
