# SCOPE: os-only
"""Portability probe for rules/cosd-secure-api.md — ADR-260 dual-auth schema.

These probes exercise behavioral guarantees that the rule file documents the
Grant authentication scheme and a deprecation timeline. The Markdown content
is parsed and structural relationships between sections are validated — a
revert of the integration breaks the parser invariants.
"""

from __future__ import annotations

import re
from pathlib import Path

RULE_PATH = Path(__file__).resolve().parents[3] / "rules" / "cosd-secure-api.md"


def _extract_sections(text: str) -> dict[str, str]:
    """Split markdown by H2/H3 headers and return {header: body}."""
    sections: dict[str, str] = {}
    current_header = "_preamble"
    current_lines: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{2,4}\s+(.+)$", line)
        if match:
            sections[current_header] = "\n".join(current_lines)
            current_header = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections[current_header] = "\n".join(current_lines)
    return sections


def test_grant_scheme_section_documents_format():
    """The rule must contain a section that names the Grant scheme AND its
    wire prefix v1: — otherwise the parser cannot align with cosd_grant.py."""
    text = RULE_PATH.read_text()
    sections = _extract_sections(text)

    grant_carrying = [h for h, body in sections.items() if "Authorization: Grant" in body or "Grant" in h]
    assert grant_carrying, "no section mentions Grant scheme"

    grant_body = "\n".join(sections[h] for h in grant_carrying)
    assert "v1:" in grant_body or "v1:" in text, "Grant wire-format prefix v1: missing"
    assert "ADR-260" in text, "Rule does not cite ADR-260"


def test_deprecation_timeline_consistency():
    """The deprecation timeline must reference Bearer (legacy) AND a multi-version
    horizon (N+1 / N+2). A single-version timeline is a regression."""
    text = RULE_PATH.read_text().lower()
    assert "bearer" in text, "legacy Bearer scheme not referenced"
    assert "deprecat" in text, "deprecation timeline missing"

    horizon_pattern = re.search(r"n\s*\+\s*[12]", text)
    assert horizon_pattern is not None, (
        "deprecation horizon (N+1 or N+2) not stated; single-version timeline is a regression"
    )


def test_section_ordering_grant_before_transition_section():
    """Dedicated Grant Scheme section must appear before the Transition Timeline
    section — readers should learn the replacement before the removal plan."""
    text = RULE_PATH.read_text()
    grant_section_idx = text.find("## Grant Scheme")
    transition_idx = text.find("## Transition Timeline")
    assert grant_section_idx > 0, "missing dedicated '## Grant Scheme' section"
    assert transition_idx > 0, "missing dedicated '## Transition Timeline' section"
    assert grant_section_idx < transition_idx, (
        "Grant Scheme section must come before Transition Timeline"
    )
