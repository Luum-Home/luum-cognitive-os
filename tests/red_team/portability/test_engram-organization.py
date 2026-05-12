# SCOPE: both
"""Portability probe for rules/engram-organization.md.

The rule is SCOPE: both — it must be consumer-neutral. After Tier 3 of
the case-study leak audit, no client-project service tokens may remain
in the rule body.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _token_loader import load_blocked_tokens  # noqa: E402

tokens, _source_label = load_blocked_tokens()

REPO_ROOT = Path(__file__).resolve().parents[3]
RULE = REPO_ROOT / "rules" / "engram-organization.md"

def test_rule_exists() -> None:
    assert RULE.exists(), "rules/engram-organization.md is missing"


def test_rule_contains_no_consumer_tokens() -> None:
    """Falsification probe: rule must not embed client service names."""
    tokens, source_label = load_blocked_tokens()
    text = RULE.read_text(encoding="utf-8")
    found = sorted({tok for tok in tokens if tok in text})
    assert not found, (
        f"rules/engram-organization.md leaks consumer tokens: {found}. "
        "Tier 3 of the case-study leak audit (see "
        "docs/09-Quality/legal/pre-public-readiness-checklist.md C2) requires the "
        "rule body to use generic placeholders only."
    )
