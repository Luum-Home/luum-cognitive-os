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


def package_skill_proof_slug(rel: str) -> str | None:
    """Return the package-skill-specific proof slug.

    Package skills live at packages/<package>/skills/<skill>/SKILL.md. They are
    portable package surfaces, not root skills, so they must not collapse to the
    unusable shared `test_SKILL.py` proof path.
    """
    path = Path(rel)
    if (
        rel.startswith("packages/")
        and path.name == "SKILL.md"
        and len(path.parts) >= 5
        and path.parts[2] == "skills"
    ):
        package = path.parts[1].replace("-", "_")
        skill = path.parts[3].replace("-", "_")
        return f"{package}_{skill}"
    return None


def family_proof_candidates(rel: str) -> list[str]:
    """Return accepted family-level portability proofs for coherent primitive groups."""
    path = Path(rel)
    candidates: list[str] = []
    artifact_members = {
        "scripts/cos-artifact-ingest",
        "scripts/cos-artifact-watch",
        "scripts/cos-artifact-report",
        "scripts/cos-work-graph",
        "scripts/cos-refutation-review",
        "scripts/cos-second-pass-advisor",
        "skills/artifact-workflow/SKILL.md",
    }
    lean_skillopt_members = {
        "scripts/cos-lean-review",
        "scripts/cos-lean-audit",
        "scripts/cos-lean-debt",
        "scripts/cos-skill-opt-run",
        "scripts/cos-skill-edit-gate",
        "scripts/cos-skill-proposal-stage",
        "scripts/cos-skill-adopt",
        "scripts/cos-skill-rejected-buffer",
        "scripts/cos-skill-slow-update",
        "scripts/cos-skill-sleep",
        "skills/lean-code/SKILL.md",
        "skills/skill-optimization/SKILL.md",
    }
    so_impact_members = {
        "scripts/cos-so-impact-eval",
        "skills/so-impact-eval/SKILL.md",
        "templates/so-impact-eval.example.yaml",
    }
    epistemic_review_members = {
        "scripts/cos-claim-audit",
        "scripts/cos-evidence-rank",
        "scripts/cos-benchmark-gaming-audit",
        "scripts/cos_epistemic_review.py",
        "skills/epistemic-review/SKILL.md",
    }
    agent_supervision_members = {
        "scripts/cos-agent-run-status",
        "scripts/cos-agent-watch",
        "scripts/cos-progress-metric",
        "scripts/cos-handoff-if-dead",
        "scripts/cos_agent_supervision.py",
        "skills/agent-run-supervision/SKILL.md",
    }
    if rel in artifact_members:
        candidates.append(f"{PORTABILITY_DIR}/test_cos_artifact_workflow_primitives.py")
    if rel in lean_skillopt_members:
        candidates.append(f"{PORTABILITY_DIR}/test_cos_lean_skillopt_primitives.py")
    if rel in so_impact_members:
        candidates.append(f"{PORTABILITY_DIR}/test_cos_so_impact_eval_primitive.py")
    if rel in epistemic_review_members:
        candidates.append(f"{PORTABILITY_DIR}/test_cos_epistemic_review_primitives.py")
    if rel in agent_supervision_members:
        candidates.append(f"{PORTABILITY_DIR}/test_cos_agent_supervision_primitives.py")
    return candidates


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
    package_skill_slug = package_skill_proof_slug(rel)
    candidates.extend(family_proof_candidates(rel))
    if skill_slug:
        candidates.append(f"{PORTABILITY_DIR}/test_skill_{skill_slug}.py")
    if package_skill_slug:
        candidates.append(f"{PORTABILITY_DIR}/test_package_skill_{package_skill_slug}.py")
        candidates.append(f"{PORTABILITY_DIR}/test_package_skills.py")
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
    if skill_proof_slug(rel) or package_skill_proof_slug(rel):
        return candidates[0]
    return candidates[3]
