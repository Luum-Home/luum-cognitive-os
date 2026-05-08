# SCOPE: both
"""Portability proof for verification-before-completion SKILL.md.

Asserts that no consumer-project service names leak into the SKILL source.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "packages" / "verification-audit" / "skills" / "verification-before-completion" / "SKILL.md"

LEAKED_TOKENS = (
    "consumer-alpha",
    "consumer-beta",
    "service-alpha",
    "service-beta",
    "Consumer Alpha",
    "service-gamma",
    "service-alpha-go",
    "example-services/",
    "services/example",
)


def test_skill_file_exists() -> None:
    assert SKILL.is_file(), f"skill source missing: {SKILL}"


def test_no_consumer_tokens_in_skill_source() -> None:
    text = SKILL.read_text(encoding="utf-8")
    leaks = [tok for tok in LEAKED_TOKENS if tok in text]
    assert not leaks, (
        f"Consumer-project leak in {SKILL.relative_to(REPO_ROOT)}: {leaks}. "
        "Replace with generic placeholders like `<service-a>`."
    )


def test_falsification_guard_detects_seeded_token(tmp_path: Path) -> None:
    """Falsification probe: if we deliberately seed a leak, the gate must fail."""
    decoy = tmp_path / "DECOY.md"
    decoy.write_text("This file mentions consumer-alpha for the test.", encoding="utf-8")
    text = decoy.read_text(encoding="utf-8")
    leaks = [tok for tok in LEAKED_TOKENS if tok in text]
    assert leaks, "falsification probe failed: known leak token was not detected"
