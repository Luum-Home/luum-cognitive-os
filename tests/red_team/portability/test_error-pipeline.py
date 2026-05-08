# SCOPE: both
"""Portability probes for hooks/error-pipeline.sh.

The hook is SCOPE: both — it must work for any consumer of this OS, not
only the one consumer whose service names historically leaked into the
hook source. These probes falsify the post-Tier-1 invariant that no
consumer-specific identifiers remain in the executable hook code.
"""

from __future__ import annotations

import re  # noqa: F401 — kept for future structural probes
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "error-pipeline.sh"
TEMPLATE = REPO_ROOT / "templates" / "service-map.example.yaml"


# Curated list of identifiers that must NOT appear in the hook source
# after the Tier 1 refactor. Reappearance falsifies the portability claim.
LEAKED_TOKENS = (
    "consumer-beta",
    "service-alpha",
    "onboarding",
    "consumer-alpha",
    "service-beta",
    "monolith",
    "service-gamma",
)


def test_hook_source_contains_no_consumer_tokens() -> None:
    """Falsification probe: the hook must not embed client service names."""
    src = HOOK.read_text(encoding="utf-8")
    found = sorted({tok for tok in LEAKED_TOKENS if tok in src})
    assert not found, (
        f"hooks/error-pipeline.sh leaks consumer tokens: {found}. "
        "Tier 1 of the case-study leak audit (see "
        "docs/legal/pre-public-readiness-checklist.md C2) requires the "
        "hook to be config-driven via .cognitive-os/private/service-map.yaml — "
        "no client identifiers should remain in the hook source itself."
    )


def test_template_exists_and_is_documented() -> None:
    """The operator template must exist and be self-documenting."""
    assert TEMPLATE.exists(), (
        "templates/service-map.example.yaml is missing. The hook is "
        "config-driven; without the template, operators have no way to "
        "discover the configuration contract."
    )
    text = TEMPLATE.read_text(encoding="utf-8")
    # Self-documenting: must explain where to install and the format.
    assert ".cognitive-os/private/service-map.yaml" in text
    assert "format" in text.lower() or "schema" in text.lower()


def test_template_does_not_leak_real_consumer_names() -> None:
    """The template's example values must be illustrative, not real."""
    text = TEMPLATE.read_text(encoding="utf-8")
    # Allow names appearing inside comments that explain what NOT to do
    # by stripping comment lines first.
    non_comment = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    found = sorted({tok for tok in LEAKED_TOKENS if tok in non_comment})
    assert not found, (
        f"template service-map.example.yaml leaks real consumer names: "
        f"{found}. Use illustrative placeholders instead."
    )
