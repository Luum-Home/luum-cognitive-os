# SCOPE: both
"""Portability proof for resume-tasks SKILL.md."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL = REPO_ROOT / "packages" / "agent-lifecycle" / "skills" / "resume-tasks" / "SKILL.md"

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
        f"Consumer-project leak in {SKILL.relative_to(REPO_ROOT)}: {leaks}."
    )


def test_falsification_guard_detects_seeded_token(tmp_path: Path) -> None:
    decoy = tmp_path / "DECOY.md"
    decoy.write_text("seeded leak: service-beta migration", encoding="utf-8")
    text = decoy.read_text(encoding="utf-8")
    leaks = [tok for tok in LEAKED_TOKENS if tok in text]
    assert leaks, "falsification probe failed: seeded token not caught"
