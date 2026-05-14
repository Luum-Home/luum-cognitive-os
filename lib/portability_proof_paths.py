# SCOPE: os-only
"""Canonical paths for paired portability proofs."""

from __future__ import annotations

from pathlib import Path

PORTABILITY_DIR = "tests/red_team/portability"


def skill_proof_slug(rel: str) -> str | None:
    """Return the skill-specific proof slug for skills/<name>/SKILL.md."""
    path = Path(rel)
    if rel.startswith("skills/") and path.name == "SKILL.md" and len(path.parts) >= 3:
        return path.parent.name.replace("-", "_")
    return None


def paired_candidates(rel: str) -> list[str]:
    """Return accepted portability proof paths for an artifact.

    The non-skill candidates intentionally match hooks/scope-marker-portability-gate.sh.
    The skill-specific candidate avoids every skill sharing the unusable `test_SKILL.py`
    proof name while remaining deterministic for scaffolders and audits.
    """
    base = Path(rel).name
    stem = base.rsplit(".", 1)[0]
    candidates: list[str] = []
    skill_slug = skill_proof_slug(rel)
    if skill_slug:
        candidates.append(f"{PORTABILITY_DIR}/test_skill_{skill_slug}.py")
    candidates.extend(
        [
            f"{PORTABILITY_DIR}/{stem}.bats",
            f"{PORTABILITY_DIR}/{base}.bats",
            f"{PORTABILITY_DIR}/{stem}_test.py",
            f"{PORTABILITY_DIR}/test_{stem}.py",
        ]
    )
    return candidates


def suggested_test_path(rel: str) -> str:
    """Return the canonical path a scaffold should create for a missing proof."""
    candidates = paired_candidates(rel)
    if skill_proof_slug(rel):
        return candidates[0]
    return candidates[3]
