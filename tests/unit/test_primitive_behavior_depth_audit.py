from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_behavior_depth_audit.py"
spec = importlib.util.spec_from_file_location("primitive_behavior_depth_audit", MODULE_PATH)
assert spec and spec.loader
primitive_behavior_depth_audit = importlib.util.module_from_spec(spec)
sys.modules["primitive_behavior_depth_audit"] = primitive_behavior_depth_audit
spec.loader.exec_module(primitive_behavior_depth_audit)

DepthRow = primitive_behavior_depth_audit.DepthRow


def test_test_depth_classification_keeps_portability_distinct_from_adversarial() -> None:
    assert primitive_behavior_depth_audit._test_depth("tests/red_team/portability/test_scope-creep-detector.py") == "projection"
    assert primitive_behavior_depth_audit._test_depth("tests/red_team/portability/test_os_only_scope_family.py") == "structural"
    assert primitive_behavior_depth_audit._test_depth("tests/chaos/test_destructive_rm_blocker.py") == "adversarial"
    assert primitive_behavior_depth_audit._test_depth("tests/behavior/test_cos_status.py") == "functional"


def test_minimum_depth_policy_flags_below_required(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "primitive-scope-classification.yaml").write_text(
        "behavior_depth_policy:\n"
        "  minimum_by_scope:\n"
        "    both: projection\n",
        encoding="utf-8",
    )
    rows = [DepthRow("rules/a.md", "rules", "both", "user-plane", "family", "structural", "fixture", ["tests/x.py"])]

    findings = primitive_behavior_depth_audit._minimum_depth_findings(tmp_path, rows)

    assert findings[0].code == "behavior-depth-below-minimum"


def test_depth_budget_flags_regression(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "primitive-scope-classification.yaml").write_text(
        "behavior_depth_policy:\n"
        "  max_by_depth:\n"
        "    structural: 0\n",
        encoding="utf-8",
    )
    rows = [DepthRow("rules/a.md", "rules", "both", "user-plane", "family", "structural", "fixture", ["tests/x.py"])]

    findings = primitive_behavior_depth_audit._budget_findings(tmp_path, rows)

    assert findings[0].code == "behavior-depth-budget-exceeded"


def test_artifact_name_does_not_leak_a_structural_claim_into_a_projection_proof() -> None:
    """A cwd-invariance probe stays projection even when the ARTIFACT is a "readiness" script.

    Regression guard: the classifier used to match STRUCTURAL_RE against the whole
    test path, so the token ``readiness`` -- inherited from the artifact's own stem
    via the ``test_<artifact-stem>.py`` naming convention -- filed a portability
    probe as a structural proof.
    """
    depth = primitive_behavior_depth_audit._test_depth(
        "tests/red_team/portability/test_check_codebase_memory_readiness.py",
        "scripts/check_codebase_memory_readiness.py",
    )
    assert depth == "projection"
    for test, artifact in (
        ("tests/red_team/portability/test_pentesting-readiness.py", "rules/pentesting-readiness.md"),
        ("tests/red_team/portability/test_cos-architecture-readiness.py", "scripts/cos-architecture-readiness"),
        ("tests/red_team/portability/test_cos-service-readiness-gate.py", "scripts/cos-service-readiness-gate"),
        ("tests/red_team/portability/test_primitive_fitness_ledger.py", "scripts/primitive_fitness_ledger.py"),
    ):
        assert primitive_behavior_depth_audit._test_depth(test, artifact) == "projection", test


def test_artifact_name_does_not_leak_an_adversarial_claim_into_a_projection_proof() -> None:
    """The same leak runs upward too: ``secret``/``guard`` in the artifact stem overclaimed depth 5."""
    for test, artifact in (
        ("tests/red_team/portability/test_secret-detector.py", "hooks/secret-detector.sh"),
        ("tests/red_team/portability/test_concurrent-write-guard.py", "hooks/concurrent-write-guard.sh"),
        ("tests/red_team/portability/test_security-red-team.py", "scripts/security-red-team"),
        ("tests/red_team/portability/test_skill_security_red_team.py", "skills/security-red-team/SKILL.md"),
    ):
        assert primitive_behavior_depth_audit._test_depth(test, artifact) == "projection", test


def test_a_test_named_for_its_own_subject_keeps_its_depth() -> None:
    """Reverse guard: subtracting the artifact stem must not disarm real signals.

    The family proofs are not named after any artifact, so nothing is subtracted
    and they stay structural; a genuinely adversarial unit test keeps depth 5.
    """
    assert (
        primitive_behavior_depth_audit._test_depth(
            "tests/red_team/portability/test_os_only_scope_family.py", "hooks/adoption-freeze-gate.sh"
        )
        == "structural"
    )
    assert (
        primitive_behavior_depth_audit._test_depth("tests/unit/test_codex_guard_layer.py", "hooks/codex-session-start.sh")
        == "adversarial"
    )


def test_no_detectable_leak_leaves_the_historical_match_untouched() -> None:
    """Reverse guard: with no artifact stem to subtract, classification must not shift.

    ``test_os_only_missing_proof_smoke.py`` covers 40 artifacts and is named after
    none of them. It read as ``projection`` (its lane) before the fix and must keep
    reading that way -- promoting it to ``smoke`` on the strength of the word in its
    filename would be the same name-based guess in a new place.
    """
    for artifact in ("scripts/cos-goal", "rules/goal-loop.md", "skills/install-hook/SKILL.md"):
        depth = primitive_behavior_depth_audit._test_depth(
            "tests/red_team/portability/test_os_only_missing_proof_smoke.py", artifact
        )
        assert depth == "projection", artifact
    assert (
        primitive_behavior_depth_audit._test_depth(
            "tests/red_team/portability/test_skill_ops_runbook.py", "skills/ops-runbook/SKILL.md"
        )
        == "projection"
    )
