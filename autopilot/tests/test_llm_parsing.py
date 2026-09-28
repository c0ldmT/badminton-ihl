from llm import extract_json, parse_verdict, strip_thinking


def test_strip_thinking():
    assert strip_thinking("<think>hmm {\"verdict\":\"PASS\"}</think>Antwort") == "Antwort"
    assert strip_thinking("nur gedanken</think> rest") == "rest"


def test_json_plain_and_fenced():
    assert parse_verdict('{"verdict": "PASS", "summary": "ok", "issues": []}').passed
    v = parse_verdict('Hier:\n```json\n{"verdict":"FAIL","summary":"x","issues":["a \\"b\\" c"]}\n```')
    assert v.verdict == "FAIL" and v.issues == ['a "b" c']


def test_last_object_wins_and_ignores_thinking():
    txt = ('<think>{"verdict":"PASS"}</think> Beispiel {"foo": 1} '
           'final {"verdict": "fail", "issues": "fehlt Test"}')
    v = parse_verdict(txt)
    assert v.verdict == "FAIL" and v.issues == ["fehlt Test"]


def test_braces_inside_strings():
    v = parse_verdict('{"verdict":"FAIL","issues":["Funktion f() { return 1 } fehlt"]}')
    assert v.issues == ["Funktion f() { return 1 } fehlt"]


def test_fallback_regex_and_garbage():
    assert parse_verdict("**Verdict:** PASS\nalles gut").passed
    v = parse_verdict("ich weiß nicht")
    assert v.verdict == "FAIL" and not v.parsed


def test_fail_without_issues_gets_generic_issue():
    v = parse_verdict('{"verdict":"FAIL"}')
    assert v.issues


def test_extract_json_none():
    assert extract_json("kein json") is None
