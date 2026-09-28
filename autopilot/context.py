"""Kontext-Bausteine für Prompts: Spec-Abschnitte, Repo-Übersicht, Rollen-Prompts."""
from __future__ import annotations

import re

import gitutil
from config import AGENT_PROMPTS_DIR, PROMPTS_DIR, SPEC_PATH

HEADING_RE = re.compile(r"^(#{2,3})\s+(\d+(?:\.\d+)?)\.?\s")


def spec_sections(refs: list[str], max_chars: int = 16000) -> str:
    """Holt die referenzierten Abschnitte (z. B. '3.3', '5') aus PROJECT_SPEC.md."""
    if not SPEC_PATH.exists() or not refs:
        return "(keine Spec-Abschnitte referenziert)"
    lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    heads = []
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2)))
    out = []
    for ref in refs:
        ref = ref.strip().lstrip("§")
        for idx, (i, level, num) in enumerate(heads):
            if num != ref:
                continue
            end = len(lines)
            for j, lvl2, _ in heads[idx + 1:]:
                if lvl2 <= level:
                    end = j
                    break
            out.append("\n".join(lines[i:end]).strip())
            break
    text = "\n\n".join(out) or "(Abschnitte nicht gefunden)"
    return text if len(text) <= max_chars else text[:max_chars] + "\n[... gekürzt ...]"


def repo_overview(max_lines: int = 250) -> str:
    files = [f for f in gitutil.git("ls-files").splitlines()
             if not f.startswith(("web/drizzle/meta/", "web/public/")) and not f.endswith("package-lock.json")]
    if len(files) > max_lines:
        return "\n".join(files[:max_lines]) + f"\n[... {len(files) - max_lines} weitere Dateien ...]"
    return "\n".join(files)


def agent_prompt(name: str) -> str:
    """Body einer .opencode/agents/<name>.md (ohne Frontmatter) – eine Quelle für beide Modi."""
    text = (AGENT_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return text.strip()


def local_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
