"""Lesen und Schreiben von TASKS.md (deterministisch, ohne LLM).

CLI:  python3 autopilot/tasks.py list | next | set <ID> <status> [Grund]
Nur Standardbibliothek, damit Skripte es ohne venv nutzen können.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

TASKS_PATH = Path(__file__).resolve().parent.parent / "TASKS.md"

HEADER_RE = re.compile(r"^###\s+(T\d{3,})\s*[·:\-–—]\s*(.+?)\s*$")
META_RE = re.compile(r"^status:\s*([\w-]+)\s*\|\s*depends:\s*([^|]*?)\s*\|\s*spec:\s*(.*?)\s*$")
VALID_STATUS = {"open", "done", "blocked"}


@dataclass
class Task:
    id: str
    title: str
    status: str
    depends: list[str] = field(default_factory=list)
    spec: list[str] = field(default_factory=list)
    block: str = ""          # kompletter Markdown-Block inkl. Überschrift

    @property
    def label(self) -> str:
        return f"{self.id} · {self.title}"


def _split_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw in ("", "-"):
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def parse(text: str) -> list[Task]:
    lines = text.splitlines()
    tasks: list[Task] = []
    i = 0
    while i < len(lines):
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        start = i
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        meta = META_RE.match(lines[j]) if j < len(lines) else None
        if not meta:
            raise ValueError(f"TASKS.md Zeile {j + 1}: Meta-Zeile für {m.group(1)} fehlt oder ist ungültig")
        end = j + 1
        while end < len(lines) and not lines[end].startswith("### ") and not lines[end].startswith("## "):
            end += 1
        tasks.append(Task(
            id=m.group(1), title=m.group(2), status=meta.group(1).lower(),
            depends=_split_list(meta.group(2)), spec=_split_list(meta.group(3)),
            block="\n".join(lines[start:end]).strip(),
        ))
        i = end
    ids = [t.id for t in tasks]
    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        raise ValueError(f"TASKS.md: doppelte IDs {sorted(dupes)}")
    return tasks


def load(path: Path = TASKS_PATH) -> list[Task]:
    return parse(path.read_text(encoding="utf-8"))


def deps_done(task: Task, by_id: dict[str, Task]) -> bool:
    return all(d in by_id and by_id[d].status == "done" for d in task.depends)


def next_task(tasks: list[Task], only_id: str | None = None) -> Task | None:
    by_id = {t.id: t for t in tasks}
    if only_id:
        t = by_id.get(only_id)
        if t is None:
            raise ValueError(f"Task {only_id} existiert nicht")
        if t.status != "open":
            raise ValueError(f"Task {only_id} hat Status '{t.status}', erwartet 'open'")
        if not deps_done(t, by_id):
            missing = [d for d in t.depends if by_id.get(d) is None or by_id[d].status != "done"]
            raise ValueError(f"Task {only_id}: Abhängigkeiten nicht erledigt: {missing}")
        return t
    for t in tasks:
        if t.status == "open" and deps_done(t, by_id):
            return t
    return None


def set_status(task_id: str, status: str, note: str | None = None, path: Path = TASKS_PATH) -> None:
    if status not in VALID_STATUS:
        raise ValueError(f"Ungültiger Status {status}")
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = HEADER_RE.match(line)
        if not m or m.group(1) != task_id:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        meta = META_RE.match(lines[j])
        if not meta:
            raise ValueError(f"Meta-Zeile für {task_id} ungültig")
        lines[j] = f"status: {status} | depends: {meta.group(2).strip() or '-'} | spec: {meta.group(3).strip()}"
        # alte BLOCKED-Zeilen direkt unter der Meta-Zeile entfernen
        k = j + 1
        while k < len(lines) and lines[k].startswith("> BLOCKED"):
            del lines[k]
        if status == "blocked" and note:
            one_line = " ".join(note.split())[:400]
            lines.insert(j + 1, f"> BLOCKED: {one_line}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    raise ValueError(f"Task {task_id} nicht gefunden")


def _cli(argv: list[str]) -> int:
    if not argv or argv[0] == "list":
        for t in load():
            print(f"{t.id:5} {t.status:8} deps={','.join(t.depends) or '-':12} {t.title}")
        return 0
    if argv[0] == "next":
        t = next_task(load())
        print(t.label if t else "(keine offene Task mit erfüllten Abhängigkeiten)")
        return 0
    if argv[0] == "set" and len(argv) >= 3:
        set_status(argv[1], argv[2], " ".join(argv[3:]) or None)
        print(f"{argv[1]} -> {argv[2]}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
