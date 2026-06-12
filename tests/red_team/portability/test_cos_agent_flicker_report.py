# SCOPE: os-only
"""Portability proof for scripts/cos_agent_flicker_report.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/cos_agent_flicker_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cos_agent_flicker_report_portability", ARTIFACT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_cos_agent_flicker_report_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_build_report_accepts_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: report builder must not depend on OS repo cwd."""
    module = _load_module()
    payload = module.build_report(tmp_path)
    assert payload["schema_version"] == module.SCHEMA_VERSION
    assert payload["summary"]["control_count"] == 10
    assert payload["status"] in {"pass", "warn", "fail"}
