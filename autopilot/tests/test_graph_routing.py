from config import SETTINGS
from graph import build_graph, route_gate
from opencode_runner import TEXT_TOOLCALL_RE, parse_events


def test_route_gate():
    r = route_gate("checks")
    assert r({"gate_passed": True, "revision": 99}) == "checks"
    assert r({"gate_passed": False, "revision": 1}) == "coder"
    assert r({"gate_passed": False, "revision": SETTINGS.max_revisions}) == "blocked"


def test_graph_compiles():
    nodes = set(build_graph().get_graph().nodes)
    assert {"select_task", "brief", "coder", "checks", "spec_review", "quality_review", "done", "blocked"} <= nodes


def test_parse_events_takes_last_message_text():
    lines = [
        '{"type":"text","part":{"messageID":"m1","text":"zwischendurch"}}',
        '{"type":"tool_use","part":{"tool":"bash","state":{"status":"completed"}}}',
        '{"type":"tool_use","part":{"tool":"edit","state":{"status":"error"}}}',
        'kein json',
        '{"type":"text","part":{"messageID":"m2","text":"GEÄNDERT: a.ts"}}',
    ]
    final, tools, errors = parse_events(lines)
    assert final == "GEÄNDERT: a.ts" and tools == 2 and errors == 1


def test_text_toolcall_detection():
    assert TEXT_TOOLCALL_RE.search("<tool_call>\n<function=bash>")
    assert TEXT_TOOLCALL_RE.search('{"name": "bash", "arguments": {}}')
    assert not TEXT_TOOLCALL_RE.search("GEÄNDERT: web/src/domain/elo.ts")
