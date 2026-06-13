# SCOPE: os-only
"""Portability proof for scripts/cos_pytest_lastfailed_health.py."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "scripts" / "cos_pytest_lastfailed_health.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("cos_pytest_lastfailed_health_portability", ARTIFACT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_module_exists() -> None:
    assert ARTIFACT.exists()


def test_empty_cache_reports_pass_for_arbitrary_project_root(tmp_path: Path) -> None:
    module = _load_module()
    report = module.build_report(tmp_path, verify=False, clear_stale=False, timeout_seconds=1)
    assert report["status"] == "pass"
    assert report["cache_state"] == "empty"


def test_stale_cache_clears_only_after_verified_pass(tmp_path: Path) -> None:
    """Falsification probe: clear-stale must not delete cache without passing --lf verification."""
    module = _load_module()
    cache = tmp_path / ".pytest_cache" / "v" / "cache" / "lastfailed"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"tests/unit/test_old.py::test_old": True}), encoding="utf-8")
    with patch.object(module, "run_lastfailed", return_value={"status": "pass", "returncode": 0}):
        report = module.build_report(tmp_path, verify=True, clear_stale=True, timeout_seconds=1)
    assert report["cleared"] is True
    assert not cache.exists()


def test_active_failure_preserves_cache(tmp_path: Path) -> None:
    module = _load_module()
    cache = tmp_path / ".pytest_cache" / "v" / "cache" / "lastfailed"
    cache.parent.mkdir(parents=True)
    cache.write_text(json.dumps({"tests/unit/test_old.py::test_old": True}), encoding="utf-8")
    with patch.object(module, "run_lastfailed", return_value={"status": "fail", "returncode": 1}):
        report = module.build_report(tmp_path, verify=True, clear_stale=True, timeout_seconds=1)
    assert report["status"] == "warn"
    assert cache.exists()
