from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_scope_health.py"
spec = importlib.util.spec_from_file_location("primitive_scope_health", MODULE_PATH)
assert spec and spec.loader
primitive_scope_health = importlib.util.module_from_spec(spec)
sys.modules["primitive_scope_health"] = primitive_scope_health
spec.loader.exec_module(primitive_scope_health)

HealthRow = primitive_scope_health.HealthRow


def test_infer_plane_separates_control_factory_user_and_runtime(tmp_path: Path) -> None:
    root = tmp_path
    assert primitive_scope_health.infer_plane(root, "scripts/primitive_scope_classifier.py", "os-only", {}) == "control-plane"
    assert primitive_scope_health.infer_plane(root, "skills/primitive-harvester/SKILL.md", "both", {}) == "factory-plane"
    assert primitive_scope_health.infer_plane(root, "templates/project-templates/go/README.md.tmpl", "project", {}) == "user-plane"
    assert primitive_scope_health.infer_plane(root, "hooks/secret-detector.sh", "both", {}) == "runtime-plane"


def test_false_both_requires_source_path_or_weak_proof_with_internal_markers(tmp_path: Path) -> None:
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "shared.sh").write_text("# SCOPE: both\nSee docs/02-Decisions/adrs/ADR-001.md\n")
    rows = [
        HealthRow(
            path="hooks/shared.sh",
            kind="hooks",
            scope="both",
            declared_scope="both",
            confidence="high",
            plane="runtime-plane",
            consumer_surface="shared",
            proof_level="family",
            decision_source="fixture",
            paired_portability_test="tests/red_team/portability/test_shared_hook_surfaces.py",
        )
    ]
    assert primitive_scope_health.false_both_findings(tmp_path, rows) == []

    weak = [rows[0].__class__(**{**rows[0].__dict__, "proof_level": "batch"})]
    findings = primitive_scope_health.false_both_findings(tmp_path, weak)
    assert findings[0].code == "both-needs-specific-proof"


def test_false_both_source_path_detector_does_not_flag_lowercase_route_segments(tmp_path: Path) -> None:
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "scope.md").write_text(
        '<!-- SCOPE: both -->\nExample approved scope: "internal/users/handler.go"\n'
    )
    rows = [
        HealthRow(
            path="rules/scope.md",
            kind="rules",
            scope="both",
            declared_scope="both",
            confidence="high",
            plane="user-plane",
            consumer_surface="shared",
            proof_level="primitive-specific",
            decision_source="fixture",
            paired_portability_test="tests/red_team/portability/test_scope.py",
        )
    ]

    assert primitive_scope_health.false_both_findings(tmp_path, rows) == []


def test_generic_os_only_detector_finds_repo_facing_internalization_candidate(tmp_path: Path) -> None:
    (tmp_path / "skills" / "browser-task").mkdir(parents=True)
    (tmp_path / "skills" / "browser-task" / "SKILL.md").write_text(
        "<!-- SCOPE: os-only -->\n---\nuser-invocable: true\ntriggers:\n- browser task\n---\n# Browser Task\n"
    )
    rows = [
        HealthRow(
            path="skills/browser-task/SKILL.md",
            kind="skills",
            scope="os-only",
            declared_scope="os-only",
            confidence="high",
            plane="user-plane",
            consumer_surface="maintainer-only",
            proof_level="none",
            decision_source="fixture",
            paired_portability_test=None,
        )
    ]
    findings = primitive_scope_health.generic_os_only_findings(tmp_path, rows)
    assert findings and findings[0].code == "os-only-generic-candidate"


def test_review_exemptions_suppress_documented_findings(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "primitive-scope-classification.yaml").write_text(
        "review_exemptions:\n"
        "  os-only-generic-candidate:\n"
        "  - path: skills/cos-status/SKILL.md\n"
        "    rationale: COS-only control-plane status surface.\n",
        encoding="utf-8",
    )
    findings = [
        primitive_scope_health.Finding(
            "skills/cos-status/SKILL.md",
            "skills",
            "os-only",
            "control-plane",
            "review",
            "os-only-generic-candidate",
            "generic name",
        )
    ]

    active, suppressed = primitive_scope_health._apply_review_exemptions(tmp_path, findings)

    assert active == []
    assert suppressed == [
        {
            "path": "skills/cos-status/SKILL.md",
            "code": "os-only-generic-candidate",
            "rationale": "COS-only control-plane status surface.",
        }
    ]


def test_balance_finding_uses_expected_scope_distribution(tmp_path: Path) -> None:
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "primitive-scope-classification.yaml").write_text(
        "expected_scope_distribution:\n  skills:\n    project_min_warning: 50\n"
    )
    rows = [
        HealthRow("skills/a/SKILL.md", "skills", "os-only", "os-only", "high", "control-plane", "maintainer-only", "none", "fixture", None),
        HealthRow("skills/b/SKILL.md", "skills", "project", "project", "high", "user-plane", "project-generated", "none", "fixture", None),
    ]
    assert primitive_scope_health.balance_findings(tmp_path, rows) == []
    rows = rows[:1]
    findings = primitive_scope_health.balance_findings(tmp_path, rows)
    assert findings[0].code == "scope-ratio-project-low"
