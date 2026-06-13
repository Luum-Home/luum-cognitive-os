# SCOPE: os-only
"""Portability proof for scripts/cos_primitive_closure_check.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "scripts" / "cos_primitive_closure_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cos_primitive_closure_check_portability", ARTIFACT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_module_exists() -> None:
    assert ARTIFACT.exists()


def test_changed_context_handles_arbitrary_git_output() -> None:
    module = _load_module()
    with patch.object(module, "changed_paths", return_value={"scripts/new-tool", ".ai/context.json"}):
        context = module.closure_context()
    assert context["requires_primitive_closure"] is True
    assert context["primitive_changed_count"] == 1


def test_check_report_is_json_serializable_without_running_repo_commands() -> None:
    """Falsification probe: report assembly must not require live cwd side effects."""
    module = _load_module()
    with patch.object(module, "run_checks", return_value=[]), patch.object(module, "closure_context", return_value={"requires_primitive_closure": False}):
        report = module.build_report(repair=False)
    assert report["schema_version"] == "primitive-closure-check/v1"
    assert report["status"] == "pass"


def test_failed_step_exposes_remediation() -> None:
    module = _load_module()
    proc = Mock(returncode=1, stdout="", stderr="stale")
    with patch.object(module, "_run", return_value=proc):
        steps = module.run_checks()
    assert all(step.status == "fail" for step in steps)
    assert any(step.remediation for step in steps)
