# SCOPE: both
"""Portability proof for systematic-debugging SKILL reference docs.

Covers BOTH defense-in-depth.md AND root-cause-tracing.md under references/.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REFS_DIR = REPO_ROOT / "packages" / "verification-audit" / "skills" / "systematic-debugging" / "references"
DEFENSE = REFS_DIR / "defense-in-depth.md"
ROOT_CAUSE = REFS_DIR / "root-cause-tracing.md"

LEAKED_TOKENS = (
    "<consumer-codename-a>",
    "<consumer-codename-b>",
    "<consumer-codename-c>",
    "<consumer-service>",
    "<consumer-service-3>",
    "<consumer-service-2>",
    "<consumer-service-4>",
    "<consumer-service-5>",
    "services/acme",
)


def test_reference_files_exist() -> None:
    assert DEFENSE.is_file(), f"missing: {DEFENSE}"
    assert ROOT_CAUSE.is_file(), f"missing: {ROOT_CAUSE}"


def test_no_consumer_tokens_in_skill_source() -> None:
    leaks_per_file: dict[str, list[str]] = {}
    for ref in (DEFENSE, ROOT_CAUSE):
        text = ref.read_text(encoding="utf-8")
        leaks = [tok for tok in LEAKED_TOKENS if tok in text]
        if leaks:
            leaks_per_file[str(ref.relative_to(REPO_ROOT))] = leaks
    assert not leaks_per_file, (
        f"Consumer-project leaks in systematic-debugging references: {leaks_per_file}"
    )


def test_falsification_guard_detects_seeded_token(tmp_path: Path) -> None:
    decoy = tmp_path / "DECOY.md"
    decoy.write_text("<consumer-service-3> routes to <consumer-codename-b>", encoding="utf-8")
    text = decoy.read_text(encoding="utf-8")
    leaks = [tok for tok in LEAKED_TOKENS if tok in text]
    assert leaks, "falsification probe failed: seeded tokens not caught"
