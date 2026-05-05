"""Audit guard maturity metadata for ADR-121-S3."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.audit

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "hook_quality_audit.py"
MANIFEST = REPO / "manifests" / "hook-quality.yaml"

spec = importlib.util.spec_from_file_location("hook_quality_audit", SCRIPT)
assert spec and spec.loader
hook_quality_audit = importlib.util.module_from_spec(spec)
sys.modules["hook_quality_audit"] = hook_quality_audit
spec.loader.exec_module(hook_quality_audit)


def test_generated_guard_maturity_defaults_never_start_in_block_mode() -> None:
    desired = hook_quality_audit.desired_manifest({})
    invalid = [hook_id for hook_id, entry in desired["hooks"].items() if entry["maturity"] in {"block", "emergency"}]

    assert not invalid, "New/generated guards must start observe or warn: " + ", ".join(invalid)


def test_blocking_guard_maturity_requires_false_positive_coverage() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for hook_id, entry in manifest["hooks"].items():
        if entry.get("maturity") not in {"block", "emergency"}:
            continue
        tests = [test_path for test_path in entry.get("false_positive_tests", []) if (REPO / str(test_path)).is_file()]
        if not tests:
            failures.append(hook_id)

    assert not failures, "Block/emergency guards need false-positive coverage: " + ", ".join(failures)


def test_guard_maturity_audit_reports_invalid_manual_block_override(tmp_path: Path) -> None:
    hook = "manual-block-guard"
    manifest = hook_quality_audit.desired_manifest({})
    manifest["hooks"][hook] = {
        "script": "hooks/direct-main-guard.sh",
        "event": "PreToolUse",
        "matcher": "Bash",
        "scope": "os-only",
        "criticality": "coordination",
        "max_runtime_ms": 1000,
        "safe_degradation": "warn_and_continue_unless_exit_2",
        "maturity": "block",
        "bypass_policy": "explicit_operator_override_with_metric",
        "false_positive_tests": [],
        "harness_tiers": {"claude": "native", "codex": "native"},
        "behavior_tests": [],
    }
    quality = tmp_path / "hook-quality.yaml"
    quality.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")

    original = hook_quality_audit.QUALITY_MANIFEST
    try:
        hook_quality_audit.QUALITY_MANIFEST = quality
        failures, _report = hook_quality_audit.audit()
    finally:
        hook_quality_audit.QUALITY_MANIFEST = original

    assert any("manual-block-guard is block but has no false_positive_tests" in failure for failure in failures)
