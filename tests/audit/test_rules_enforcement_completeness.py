"""Completeness guard for test_rules_enforcement.py.

The rules-enforcement parametric matrix runs every rule × scenario combo. Many
cells legitimately skip (rule has no .sh references, rule in SETTINGS_WIRING_EXEMPT,
rule in COMPACT_EXEMPT). That's by design.

What we want to catch:
  1. A rule in rules/ that is invisible to the parametric matrix (not in
     RULE_PATHS).
  2. A rule with ALL cells skipped — no scenario actually touches it.

Approach: import the parametric module and inspect its RULE_PATHS list and
its exempt sets. Cross-reference against rules/*.md on disk.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.audit import test_rules_enforcement as re_mod

pytestmark = [pytest.mark.audit]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RULES_DIR = PROJECT_ROOT / "rules"

# Meta-docs that are not rules themselves.
META_DOCS = {"RULES-COMPACT.md", "ROADMAP.md"}


def _rule_files_on_disk() -> set[str]:
    return {p.name for p in RULES_DIR.glob("*.md")}


def test_parametric_module_discovers_rules():
    """Sanity: RULE_PATHS in the parametric module is populated."""
    assert len(re_mod.RULE_PATHS) >= 20, (
        f"Expected >=20 rule files in RULE_PATHS, got {len(re_mod.RULE_PATHS)}."
    )


def test_every_rule_on_disk_is_in_parameter_set():
    """Every rule file must appear in the parametric RULE_PATHS list.

    If a rule exists on disk but is not parameterized, none of the enforcement
    tests will check it — silent coverage gap.
    """
    on_disk = _rule_files_on_disk()
    parametric = {p.name for p in re_mod.RULE_PATHS}

    missing = on_disk - parametric
    assert not missing, (
        f"{len(missing)} rule(s) exist in rules/ but are not in RULE_PATHS: "
        f"{sorted(missing)}. Fix _all_rule_files() in test_rules_enforcement.py."
    )


def test_every_rule_has_at_least_one_applicable_scenario():
    """Every non-meta rule must be hit by at least one non-skipping scenario.

    The parametric tests are:
      - test_every_rule_in_compact_index: skips if rule is in COMPACT_EXEMPT
      - test_every_hook_enforced_rule_has_live_hook: skips if no .sh refs
        OR in SETTINGS_WIRING_EXEMPT OR all refs missing on disk
      - test_no_rule_references_missing_file: always applies (checks file refs)

    So every rule is hit by test_no_rule_references_missing_file (at minimum).
    This test asserts that the floor test covers every non-meta rule.
    """
    on_disk = _rule_files_on_disk() - META_DOCS
    parametric = {p.name for p in re_mod.RULE_PATHS}

    uncovered = on_disk - parametric
    assert not uncovered, (
        f"{len(uncovered)} non-meta rule(s) have zero applicable scenarios: "
        f"{sorted(uncovered)}. They are invisible to the enforcement matrix."
    )


def test_compact_exempt_references_existing_files():
    """COMPACT_EXEMPT must only list real files.

    A stale entry there silences the compact-index check for a file that
    doesn't exist — dead exemption.
    """
    on_disk = _rule_files_on_disk()
    stale = re_mod.COMPACT_EXEMPT - on_disk
    assert not stale, (
        f"COMPACT_EXEMPT references {len(stale)} non-existent rule file(s): "
        f"{sorted(stale)}. Remove them."
    )


def test_settings_wiring_exempt_references_existing_files():
    """SETTINGS_WIRING_EXEMPT must only list real files."""
    on_disk = _rule_files_on_disk()
    stale = set(re_mod.SETTINGS_WIRING_EXEMPT.keys()) - on_disk
    assert not stale, (
        f"SETTINGS_WIRING_EXEMPT references {len(stale)} non-existent rule "
        f"file(s): {sorted(stale)}. Remove them."
    )


def test_meta_docs_are_exempt_from_compact_index():
    """RULES-COMPACT.md and ROADMAP.md must appear in COMPACT_EXEMPT.

    If they slip out, the parametric test will fail spuriously on them.
    """
    missing = META_DOCS - re_mod.COMPACT_EXEMPT
    assert not missing, (
        f"Meta-docs missing from COMPACT_EXEMPT: {sorted(missing)}. "
        f"Add them back so they don't trip the compact-index test."
    )
