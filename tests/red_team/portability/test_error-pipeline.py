# SCOPE: os-only
"""Portability probes for hooks/error-pipeline.sh.

The hook is SCOPE: both — it must work for any consumer of this OS, not
only the one consumer whose service names historically leaked into the
hook source. These probes falsify the post-Tier-1 invariant that no
consumer-specific identifiers remain in the executable hook code.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _token_loader import load_blocked_tokens  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / "hooks" / "error-pipeline.sh"
TEMPLATE = REPO_ROOT / "templates" / "service-map.example.yaml"


def test_hook_source_contains_no_consumer_tokens() -> None:
    """Falsification probe: the hook must not embed client service names."""
    tokens, source_label = load_blocked_tokens()
    src = HOOK.read_text(encoding="utf-8")
    found = sorted({tok for tok in tokens if tok in src})
    assert not found, (
        f"hooks/error-pipeline.sh leaks consumer tokens {found} "
        f"(checked against {source_label}). Tier 1 of the case-study leak "
        f"audit requires the hook to be config-driven via "
        f".cognitive-os/private/service-map.yaml — no client identifiers "
        f"should remain in the hook source itself."
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
    tokens, source_label = load_blocked_tokens()
    text = TEMPLATE.read_text(encoding="utf-8")
    # Allow names appearing inside comments that explain what NOT to do
    # by stripping comment lines first.
    non_comment = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    found = sorted({tok for tok in tokens if tok in non_comment})
    assert not found, (
        f"template service-map.example.yaml leaks real consumer names "
        f"{found} (checked against {source_label}). "
        f"Use illustrative placeholders instead."
    )
