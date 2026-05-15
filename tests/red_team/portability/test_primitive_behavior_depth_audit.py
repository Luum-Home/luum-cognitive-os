from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "scripts" / "primitive_behavior_depth_audit.py"
WRAPPER = ROOT / "scripts" / "primitive-behavior-depth-audit"


def _load_module():
    spec = importlib.util.spec_from_file_location("primitive_behavior_depth_audit_under_test", MODULE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_behavior_depth_audit_classifies_portability_as_projection_not_adversarial() -> None:
    audit = _load_module()

    assert audit._test_depth("tests/red_team/portability/test_scope-creep-detector.py") == "projection"
    assert audit._test_depth("tests/chaos/test_destructive_rm_blocker.py") == "adversarial"
    assert audit._test_depth("tests/red_team/portability/test_os_only_scope_family.py") == "structural"


def test_behavior_depth_audit_strict_passes_current_repository() -> None:
    out = ROOT / ".cognitive-os" / "reports" / "test-primitive-behavior-depth-audit.json"
    result = subprocess.run(
        [sys.executable, str(MODULE), "--project-dir", str(ROOT), "--strict", "--json-out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout


def test_behavior_depth_wrapper_executes_module() -> None:
    out = ROOT / ".cognitive-os" / "reports" / "test-primitive-behavior-depth-wrapper.json"
    result = subprocess.run(
        [str(WRAPPER), "--project-dir", str(ROOT), "--json-out", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    assert out.exists()
