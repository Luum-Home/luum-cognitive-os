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
