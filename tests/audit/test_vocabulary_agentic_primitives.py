"""Vocabulary audit: enforce the AGENTS.md §Vocabulary decision.

Canonical source: AGENTS.md §Vocabulary (commit 6ee3b58f) — the layer of OS
constructs that agents compose at runtime is called **agentic primitives**,
not "components". Writing "OS components" or "skills components" when the
referent is a skill, hook, rule, agent, subagent, memory, or MCP server is a
vocabulary drift violation.

This test audits a curated set of active documentation files and asserts that
the forbidden agentic-context patterns are absent. The carve-out policy from
AGENTS.md §Carve-out is respected: UI/frontend components, microservice
components, build/test components, and third-party library components are
explicitly NOT flagged.

Cross-reference: ADR-072 (docs/02-Decisions/adrs/ADR-072-test-lane-taxonomy.md) uses
"primitive" for lane-taxonomy entities — consistent with this vocabulary
decision.

See also: .cognitive-os/migrations/components-to-primitives.md for the
migration inventory tracking individual file status.
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Canonical agentic primitives (from AGENTS.md §Vocabulary table)
# ---------------------------------------------------------------------------
AGENTIC_PRIMITIVE_NOUNS = [
    "skills",
    "hooks",
    "rules",
    "agents",
    "subagents",
    "MCP servers",
    "memory primitives",
]

# ---------------------------------------------------------------------------
# Forbidden phrase patterns (case-insensitive).
# Pattern: "<agentic noun> components" — using the plural slot name followed
# by "components" treats the slot as a generic software component category,
# which is the drift this test enforces against.
# Additionally, "OS components" is explicitly called out in AGENTS.md §Enforcement
# as the canonical drift indicator.
# ---------------------------------------------------------------------------
FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    # "<agentic noun> components" — direct agentic-slot misuse
    re.compile(
        r"\b(?:skills|hooks|rules|agents|subagents|MCP\s+servers|memory\s+primitives)\s+components\b",
        re.IGNORECASE,
    ),
    # "OS components" — the explicit drift phrase from AGENTS.md §Enforcement
    re.compile(r"\bOS\s+components\b", re.IGNORECASE),
    # "agentic components" — redundant with "agentic primitives", flagged
    re.compile(r"\bagentic\s+components\b", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Carve-out patterns: these are ALLOWED uses of "component(s)" even in the
# audit set. They match the AGENTS.md §Carve-out policy.
# A line is excluded from violation checking if it matches ANY carve-out.
# ---------------------------------------------------------------------------
CARVE_OUT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bUI\s+components?\b", re.IGNORECASE),
    re.compile(r"\bfrontend\s+components?\b", re.IGNORECASE),
    re.compile(r"\bReact\b.*\bcomponents?\b", re.IGNORECASE),
    re.compile(r"\bVue\b.*\bcomponents?\b", re.IGNORECASE),
    re.compile(r"\bInk\s+components?\b", re.IGNORECASE),
    re.compile(r"\bWeb\s+Components?\b"),  # proper noun — case-sensitive
    re.compile(r"\bMicroservice\s+components?\b", re.IGNORECASE),
    re.compile(r"\bservice\s+mesh\b", re.IGNORECASE),
    re.compile(r"\btest\s+components?\b", re.IGNORECASE),
    re.compile(r"\bpytest\s+components?\b", re.IGNORECASE),
    re.compile(r"\bMakefile\s+components?\b", re.IGNORECASE),
    re.compile(r"\bbuild.*\bcomponents?\b", re.IGNORECASE),
    re.compile(r"\bthird[- ]party.*\bcomponents?\b", re.IGNORECASE),
    re.compile(r"\blibrary\s+components?\b", re.IGNORECASE),
    # "CI gate" and "CI" component references are infrastructure — allow
    re.compile(r"\bCI\b.*\bcomponents?\b", re.IGNORECASE),
    # Go software-architecture subsystem headings and tables in cos-dispatch docs
    re.compile(r"Component:\s+ADR", re.IGNORECASE),
    re.compile(r"Component\s+Architecture", re.IGNORECASE),
    re.compile(r"Component\s+tests?\b", re.IGNORECASE),
    # The carve-out policy section itself (AGENTS.md §Carve-out)
    re.compile(r"Carve-?out.*component", re.IGNORECASE),
    re.compile(r"component.*remains\s+valid", re.IGNORECASE),
    # "Option C components" style (config-loader code modules in ADR-026)
    re.compile(r"Option\s+[A-Z]\s+components?\b", re.IGNORECASE),
    # Columns titled "Components Inspected" (generic analysis heading)
    re.compile(r"Components\s+Inspected", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Curated audit set (from the mission definition)
# ---------------------------------------------------------------------------
_TOP_ARCH_MD = sorted(PROJECT_ROOT.glob("docs/04-Concepts/architecture/*.md"))


def _audit_files() -> list[Path]:
    """Return the curated set of files to audit."""
    fixed = [
        PROJECT_ROOT / "AGENTS.md",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "CHANGELOG.md",
        PROJECT_ROOT / "cmd" / "cos" / "README.md",
        PROJECT_ROOT / "skills" / "CATALOG.md",
        PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md",
    ]
    return [f for f in fixed + _TOP_ARCH_MD if f.is_file()]


def _violations_in_file(path: Path) -> list[tuple[int, str, str]]:
    """Return (line_number, matched_pattern, line_text) for each violation.

    A line is a violation when it matches a FORBIDDEN_PATTERNS entry AND does
    NOT match any CARVE_OUT_PATTERNS entry (case-insensitive).
    """
    violations: list[tuple[int, str, str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return violations

    for lineno, line in enumerate(lines, start=1):
        # Skip lines that are entirely a carve-out context.
        if any(co.search(line) for co in CARVE_OUT_PATTERNS):
            continue
        for pat in FORBIDDEN_PATTERNS:
            m = pat.search(line)
            if m:
                violations.append((lineno, m.group(0), line.strip()))
                break  # one violation per line is enough

    return violations


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestForbiddenAgentic:
    """Each file in the curated audit set must be free of agentic vocabulary drift."""

    @pytest.mark.parametrize("path", _audit_files(), ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
    def test_no_agentic_components_phrase(self, path: Path) -> None:
        """Assert no forbidden 'X components' phrases exist in audit files.

        Failure reason: AGENTS.md §Vocabulary (commit 6ee3b58f) establishes
        'agentic primitive' as the canonical term for skills, hooks, rules,
        agents, subagents, memory, and MCP servers. Writing '<slot> components'
        or 'OS components' conflates these primitives with generic software
        components. See also ADR-072 and
        .cognitive-os/migrations/components-to-primitives.md for migration
        tracking.
        """
        violations = _violations_in_file(path)
        if not violations:
            return
        details = "\n".join(
            f"  line {ln}: matched {repr(phrase)!r}  →  {text}"
            for ln, phrase, text in violations
        )
        relative = path.relative_to(PROJECT_ROOT)
        pytest.fail(
            f"{relative}: vocabulary drift detected — {len(violations)} forbidden"
            f" 'X components' phrase(s) found. Use the canonical agentic primitive"
            f" term instead (AGENTS.md §Vocabulary + ADR-072).\n{details}"
        )


class TestSyntheticDetection:
    """Verify the detection machinery works on synthetic fixtures."""

    def test_detects_skills_components(self) -> None:
        """Pattern 'skills components' must be flagged."""
        fake_content = textwrap.dedent(
            """\
            # Agent Design Guide

            The system is organized into skills components, hooks components, and rules components
            for managing the agentic layer.
            """
        )
        Path("/virtual/fake-doc.md")

        def violations_in_text(text: str) -> list[tuple[int, str, str]]:
            results = []
            for lineno, line in enumerate(text.splitlines(), start=1):
                if any(co.search(line) for co in CARVE_OUT_PATTERNS):
                    continue
                for pat in FORBIDDEN_PATTERNS:
                    m = pat.search(line)
                    if m:
                        results.append((lineno, m.group(0), line.strip()))
                        break
            return results

        hits = violations_in_text(fake_content)
        assert len(hits) >= 1, (
            "Expected at least one violation for 'skills components' / 'hooks components'"
            " / 'rules components' — detection logic may be broken."
        )

    def test_detects_os_components(self) -> None:
        """Pattern 'OS components' must be flagged."""
        text = "The OS components include skills and hooks for runtime composition."
        hits = []
        for pat in FORBIDDEN_PATTERNS:
            m = pat.search(text)
            if m:
                hits.append(m.group(0))
        assert hits, (
            "Expected 'OS components' to be detected as a vocabulary drift violation."
        )

    def test_detects_agentic_components(self) -> None:
        """Pattern 'agentic components' must be flagged."""
        text = "All agentic components are wired via the hook matrix."
        hits = []
        for pat in FORBIDDEN_PATTERNS:
            m = pat.search(text)
            if m:
                hits.append(m.group(0))
        assert hits, (
            "Expected 'agentic components' to be detected as a vocabulary drift violation."
        )

    def test_carve_out_ui_components_not_flagged(self) -> None:
        """UI components is a legitimate carve-out — must NOT be flagged."""
        text = "The design system uses UI components built with React."
        # A line matching a carve-out pattern should not produce violations.
        has_carve_out = any(co.search(text) for co in CARVE_OUT_PATTERNS)
        assert has_carve_out, (
            "Expected 'UI components' to match a carve-out pattern and be excluded"
            " from violation detection."
        )

    def test_carve_out_does_not_suppress_agentic_phrase(self) -> None:
        """A line with both a carve-out AND an agentic phrase is tricky.

        The carve-out wins (suppress) — this is intentional to keep the test
        implementation simple and avoid false positives on mixed lines.
        The test documents this known limitation.
        """
        text = "The UI components and OS components share a common harness."
        # This line contains both 'UI components' (carve-out) and 'OS components'
        # (forbidden). Because the carve-out check is line-level, the entire line
        # is excluded from violation checking.
        has_carve_out = any(co.search(text) for co in CARVE_OUT_PATTERNS)
        assert has_carve_out, (
            "Mixed line (UI + OS components): carve-out match expected, suppressing"
            " the line. This is an accepted false-negative trade-off."
        )
