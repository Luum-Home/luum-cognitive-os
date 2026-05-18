"""Audit: every registered hook has a maturity field; unregistered hooks are classified.

Phase 2 acceptance criteria (operational-stability-friction-reduction.md):
- Each registered hook has maturity metadata or inherits a documented default.
- New hooks start observe/warn unless ADR-approved.
- Maturity is included in hook-quality manifest/report.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.audit]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_QUALITY = PROJECT_ROOT / "manifests" / "hook-quality.yaml"
HOOK_CLASSIFICATION = PROJECT_ROOT / "manifests" / "hook-registration-classification.yaml"
HOOKS_DIR = PROJECT_ROOT / "hooks"

VALID_MATURITY_VALUES = {"observe", "warn", "block", "emergency"}
# New hooks must start at these levels unless ADR-approved
SAFE_DEFAULT_MATURITY = {"observe", "warn"}
# Only block/emergency require ADR approval
ADR_REQUIRED_MATURITY = {"block", "emergency"}


def load_hook_quality() -> dict:
    with open(HOOK_QUALITY) as f:
        return yaml.safe_load(f)


def get_hooks_dir_scripts() -> set[str]:
    """Return stem names (no .sh) of all hook scripts in hooks/."""
    return {p.stem for p in HOOKS_DIR.glob("*.sh")}


def get_hq_referenced_scripts(data: dict) -> set[str]:
    """Return stem names of scripts referenced by hook-quality entries."""
    scripts = set()
    for entry in data.get("hooks", {}).values():
        script = entry.get("script", "")
        if script:
            scripts.add(Path(script).stem)
    return scripts


def get_classification_mentioned_scripts() -> set[str]:
    """Return stems mentioned anywhere in hook-registration-classification.yaml."""
    text = HOOK_CLASSIFICATION.read_text()
    return set(re.findall(r"hooks/([a-z0-9-]+)\.sh", text))


class TestHookQualityMaturity:
    """All entries in hook-quality.yaml must have valid maturity metadata."""

    def test_every_registered_hook_has_maturity(self):
        data = load_hook_quality()
        missing = [
            key
            for key, val in data.get("hooks", {}).items()
            if "maturity" not in val
        ]
        assert not missing, (
            f"{len(missing)} hook entries in hook-quality.yaml lack maturity: "
            f"{missing[:10]}"
        )

    def test_maturity_values_are_valid(self):
        data = load_hook_quality()
        invalid = [
            (key, val["maturity"])
            for key, val in data.get("hooks", {}).items()
            if val.get("maturity") not in VALID_MATURITY_VALUES
        ]
        assert not invalid, (
            f"Invalid maturity values found: {invalid[:10]}. "
            f"Allowed: {VALID_MATURITY_VALUES}"
        )

    def test_block_and_emergency_hooks_have_behavior_tests(self):
        """block/emergency maturity requires at least one behavior/contract test."""
        data = load_hook_quality()
        violations = []
        for key, val in data.get("hooks", {}).items():
            if val.get("maturity") in ADR_REQUIRED_MATURITY:
                tests = val.get("behavior_tests", []) + val.get("false_positive_tests", [])
                if not tests:
                    violations.append((key, val.get("maturity")))
        assert not violations, (
            f"block/emergency hooks must have behavior or false_positive tests. "
            f"Violations: {violations[:10]}"
        )

    def test_policy_section_lists_valid_maturity_values(self):
        """The policy section must enumerate all valid maturity values."""
        data = load_hook_quality()
        policy_values = set(data.get("policy", {}).get("maturity_values", []))
        assert VALID_MATURITY_VALUES == policy_values, (
            f"policy.maturity_values {policy_values} must match {VALID_MATURITY_VALUES}"
        )


class TestUnregisteredHooksClassified:
    """Every hook script NOT in hook-quality.yaml must be classified."""

    def test_no_unclassified_hook_scripts(self):
        data = load_hook_quality()
        all_scripts = get_hooks_dir_scripts()
        hq_scripts = get_hq_referenced_scripts(data)
        unregistered = all_scripts - hq_scripts

        if not unregistered:
            return  # All scripts registered — perfect

        classified = get_classification_mentioned_scripts()
        unclassified = unregistered - classified
        assert not unclassified, (
            f"{len(unclassified)} hook scripts are neither registered in hook-quality.yaml "
            f"nor classified in hook-registration-classification.yaml: "
            f"{sorted(unclassified)[:10]}"
        )

    def test_total_registered_hooks_have_maturity(self):
        """Coverage metric: fraction of registered entries with maturity >= 100%."""
        data = load_hook_quality()
        hooks = data.get("hooks", {})
        total = len(hooks)
        with_maturity = sum(1 for v in hooks.values() if "maturity" in v)
        coverage = with_maturity / total if total else 0
        assert coverage == 1.0, (
            f"Maturity coverage: {with_maturity}/{total} ({coverage:.1%}). "
            f"All registered hooks must have maturity."
        )
