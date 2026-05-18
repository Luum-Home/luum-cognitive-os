"""
Structural audit for rules/goal-loop.md.

Asserts content quality (required sections and key phrases) — not just file
existence.  This satisfies the T-12 acceptance criterion that the rule has
description front-matter and required sections.
"""
from pathlib import Path

RULE_PATH = Path(__file__).resolve().parents[2] / "rules" / "goal-loop.md"

REQUIRED_PHRASES = [
    "evidence contract",
    "structured evidence",
    "not motivational",  # surfaced as "not motivational prompts" in the text
]

REQUIRED_SECTIONS = [
    "## Purpose",
    "## Quick Reference",
    "## Writing an Evidence Contract",
    "## Enforcement Model",
]


def test_goal_rule_file_exists():
    assert RULE_PATH.exists(), f"rules/goal-loop.md not found at {RULE_PATH}"


def test_goal_rule_required_phrases():
    text = RULE_PATH.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        assert phrase in text, (
            f"Required phrase not found in rules/goal-loop.md: {phrase!r}"
        )


def test_goal_rule_required_sections():
    text = RULE_PATH.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text, (
            f"Required section not found in rules/goal-loop.md: {section!r}"
        )


def test_goal_rule_has_examples():
    """Rule must contain at least one concrete example block."""
    text = RULE_PATH.read_text(encoding="utf-8")
    assert "## Example:" in text, (
        "rules/goal-loop.md must contain at least one '## Example:' section"
    )
    assert "cos-goal create" in text, (
        "rules/goal-loop.md must show a 'cos-goal create' example"
    )


def test_goal_rule_references_architecture():
    """Rule must cross-reference the architecture concept page."""
    text = RULE_PATH.read_text(encoding="utf-8")
    assert "goal-loop.md" in text, (
        "rules/goal-loop.md must reference docs/04-Concepts/architecture/goal-loop.md"
    )


def test_goal_rule_examples_run_against_real_cli():
    """Behavioral: every fenced ```bash ``` block in the rule that invokes
    `cos-goal create` must parse via the real argparse parser. Catches stale
    examples that drift from the implemented CLI surface — broken examples are
    operator-visible bugs.

    Skips inline-table entries (single line with `<placeholder>` markers) and
    only validates multi-line fenced blocks, which are the executable examples.
    """
    import re
    import shlex
    import sys

    repo_root = RULE_PATH.resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from scripts.cos_goal import _build_parser

    parser = _build_parser()
    text = RULE_PATH.read_text(encoding="utf-8")

    # Extract bash fenced blocks
    blocks = re.findall(r"```bash\n(.*?)\n```", text, re.DOTALL)
    validated = 0
    for block in blocks:
        # Join continuation lines (backslash-newline)
        joined = re.sub(r"\\\n\s*", " ", block).strip()
        if "cos-goal create" not in joined:
            continue
        # Take just the cos-goal create ... portion of each line in the block
        for line in joined.splitlines():
            m = re.search(r"cos-goal\s+(create\s+.+)", line)
            if not m:
                continue
            argv = shlex.split(m.group(1))
            # parse_args raises SystemExit on missing required args
            parser.parse_args(argv)
            validated += 1

    assert validated >= 2, (
        f"Expected ≥2 validated cos-goal create examples in fenced blocks, got {validated}"
    )
