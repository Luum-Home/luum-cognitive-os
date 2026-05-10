"""Audit: every SKILL.md must have a non-empty, contract-compliant description.
Per ADR-067 §3 layer C — the safety net that catches anything that escapes
the template (A) and the hook (B).

Uses the REAL parser from lib/session_hygiene._fm(), not synthetic logic.
This is end-to-end: parser × disk integration.
"""
import re
import sys
import pytest
from pathlib import Path

# Use real parser to catch parser regressions too
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from session_hygiene import _fm

REPO = Path(__file__).parent.parent.parent


@pytest.mark.audit
def test_every_skill_has_extractable_nonempty_description():
    failures = []
    for skill_md in sorted((REPO / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        desc = _fm(text, "description")
        if not desc or len(desc.strip()) < 30 or desc.strip() in (">", "|", ""):
            failures.append((skill_md.parent.name, repr(desc)))
    assert not failures, (
        f"Skills with non-compliant description ({len(failures)} total): {failures}"
    )


@pytest.mark.audit
def test_every_skill_description_starts_with_use_when():
    failures = []
    for skill_md in sorted((REPO / "skills").glob("**/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        desc = _fm(text, "description")
        if not desc or not desc.strip().startswith("Use when"):
            failures.append((str(skill_md.relative_to(REPO)), repr(desc)))
    assert not failures, (
        "Skills whose routing description does not start with 'Use when' "
        f"({len(failures)} total): {failures}"
    )


@pytest.mark.audit
def test_every_skill_has_valid_audience():
    valid = {"os", "os-dev", "os-only", "project", "both", "adopters", "human"}
    failures = []
    for skill_md in sorted((REPO / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        aud = _fm(text, "audience")
        if aud and aud.strip() not in valid:
            failures.append((skill_md.parent.name, aud))
    assert not failures, f"Skills with invalid audience: {failures}"


@pytest.mark.audit
def test_every_skill_has_scope_html_comment():
    valid = {"os-only", "project", "both"}
    failures = []
    for skill_md in sorted((REPO / "skills").glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text.strip() else ""
        m = re.match(r"^\s*<!--\s*SCOPE:\s*([a-z-]+)\s*-->\s*$", first)
        if not m or m.group(1) not in valid:
            failures.append((skill_md.parent.name, first[:80]))
    assert not failures, (
        f"Skills missing/invalid <!-- SCOPE --> at line 1 ({len(failures)} total): {failures}"
    )
