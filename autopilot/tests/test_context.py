import context


def test_spec_sections_found():
    s = context.spec_sections(["3.5", "5"])
    assert "Rating-System" in s and "Datenmodell" in s
    assert "3.6 Ligatabelle" not in s          # nur der angefragte Unterabschnitt


def test_agent_prompts_have_no_frontmatter():
    for role in ("coder", "spec-reviewer", "quality-reviewer", "planner"):
        p = context.agent_prompt(role)
        assert not p.startswith("---") and "permission" not in p.splitlines()[0]
    assert '"verdict"' in context.agent_prompt("spec-reviewer")
