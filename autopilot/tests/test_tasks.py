import shutil
from pathlib import Path

import pytest

import tasks

REAL = Path(__file__).resolve().parents[2] / "TASKS.md"


def test_real_tasks_file_parses():
    ts = tasks.load(REAL)
    ids = [t.id for t in ts]
    assert ids[0] == "T001" and len(ids) == len(set(ids)) >= 30
    by = {t.id: t for t in ts}
    for t in ts:                       # alle Abhängigkeiten existieren
        assert all(d in by for d in t.depends), t.id
    assert "Akzeptanz" in by["T007"].block


def test_dependency_graph_is_acyclic():
    by = {t.id: t for t in tasks.load(REAL)}
    seen, stack = set(), set()

    def visit(i):
        assert i not in stack, f"Zyklus bei {i}"
        if i in seen:
            return
        stack.add(i)
        for d in by[i].depends:
            visit(d)
        stack.remove(i)
        seen.add(i)
    for i in by:
        visit(i)


SAMPLE = """# x
## Backlog
### T001 · Eins
status: done | depends: - | spec: 4
a
### T002 · Zwei
status: open | depends: T001 | spec: 3.1, 5
b
### T003 · Drei
status: open | depends: T004 | spec: -
c
### T004 · Vier
status: open | depends: T002 | spec: 5
d
"""


@pytest.fixture
def f(tmp_path):
    p = tmp_path / "TASKS.md"
    p.write_text(SAMPLE, encoding="utf-8")
    return p


def test_next_respects_dependencies(f):
    t = tasks.next_task(tasks.load(f))
    assert t.id == "T002" and t.spec == ["3.1", "5"]


def test_set_status_blocked_and_reopen(f):
    tasks.set_status("T002", "blocked", "zu schwer\nzweite Zeile", path=f)
    txt = f.read_text()
    assert "status: blocked | depends: T001 | spec: 3.1, 5" in txt
    assert "> BLOCKED: zu schwer zweite Zeile" in txt
    assert tasks.next_task(tasks.load(f)) is None      # T003/T004 hängen an T002
    tasks.set_status("T002", "open", path=f)
    assert "> BLOCKED" not in f.read_text()
    tasks.set_status("T002", "done", path=f)
    assert tasks.next_task(tasks.load(f)).id == "T004"


def test_only_task_validation(f):
    with pytest.raises(ValueError):
        tasks.next_task(tasks.load(f), "T003")          # Abhängigkeit offen
    with pytest.raises(ValueError):
        tasks.next_task(tasks.load(f), "T001")          # schon done
    assert tasks.next_task(tasks.load(f), "T002").id == "T002"


def test_invalid_meta_raises(tmp_path):
    p = tmp_path / "T.md"
    p.write_text("### T001 · X\nstatus open\n")
    with pytest.raises(ValueError):
        tasks.load(p)
