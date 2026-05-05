"""Contracts for the Hook Quality System manifest and audit runner."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "hook_quality_audit.py"
MANIFEST = REPO / "manifests" / "hook-quality.yaml"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("hook_quality_audit", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hook_quality_manifest_exists_and_is_current() -> None:
    assert MANIFEST.is_file(), "run `python3 scripts/hook_quality_audit.py --sync`"
    module = _load_audit_module()
    current = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    desired = module.desired_manifest(current)
    assert module.normalize(current) == module.normalize(desired), (
        "manifests/hook-quality.yaml drifted from cognitive-os.yaml; "
        "run `python3 scripts/hook_quality_audit.py --sync`."
    )


def test_hook_quality_audit_check_passes() -> None:
    result = subprocess.run(
        ["python3", str(SCRIPT), "--check"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "hook-quality: OK" in result.stdout


def test_hook_quality_manifest_covers_registered_primitives() -> None:
    module = _load_audit_module()
    registry = module.registered_hooks()
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    hooks = manifest["hooks"]
    assert set(registry) == set(hooks)
    for hook_id, entry in registry.items():
        quality = hooks[hook_id]
        assert quality["script"] == entry["script"]
        assert quality["event"] == entry["event"]
        assert quality["matcher"] == entry["matcher"]
        assert quality["scope"] == entry["scope"]


def test_hook_quality_harness_tiers_are_explicit_for_codex_and_claude() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    allowed = {"native", "governed", "cos_owned", "unsupported"}
    failures: list[str] = []
    for hook_id, entry in manifest["hooks"].items():
        tiers = entry.get("harness_tiers") or {}
        if tiers.get("claude") not in allowed:
            failures.append(f"{hook_id}: invalid claude tier {tiers.get('claude')!r}")
        if tiers.get("codex") not in allowed:
            failures.append(f"{hook_id}: invalid codex tier {tiers.get('codex')!r}")
    assert not failures, "\n".join(failures)


def test_hook_quality_manifest_declares_guard_maturity_contract() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    allowed = set(manifest["policy"]["maturity_values"])
    failures: list[str] = []
    for hook_id, entry in manifest["hooks"].items():
        if entry.get("maturity") not in allowed:
            failures.append(f"{hook_id}: invalid maturity {entry.get('maturity')!r}")
        if not entry.get("bypass_policy"):
            failures.append(f"{hook_id}: missing bypass_policy")
        if entry.get("maturity") in {"block", "emergency"}:
            tests = entry.get("false_positive_tests") or []
            existing = [path for path in tests if (REPO / path).is_file()]
            if not existing:
                failures.append(f"{hook_id}: block/emergency maturity requires false_positive_tests")
    assert not failures, "\n".join(failures)


def test_required_critical_hooks_have_behavior_coverage() -> None:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    required = manifest["policy"]["required_behavior_coverage"]
    missing: list[str] = []
    for hook_id in required:
        tests = manifest["hooks"].get(hook_id, {}).get("behavior_tests") or []
        existing = [path for path in tests if (REPO / path).is_file()]
        if not existing:
            missing.append(hook_id)
    assert not missing, "Critical hooks missing behavior coverage: " + ", ".join(missing)
