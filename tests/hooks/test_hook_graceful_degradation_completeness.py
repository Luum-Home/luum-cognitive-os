"""Completeness guard for test_hook_graceful_degradation.py.

The parametric graceful-degradation matrix tests every hook × scenario combo.
Many cells legitimately skip (a hook not in a scenario's PRIVATE_MODE_HOOKS
list, for example). That is by design.

What we DO want to catch:
  1. A hook in hooks/ that appears in NO scenario whatsoever (invisible to matrix).
  2. A hook whose every applicable scenario is gated out so it never actually runs.

Either is a signal the matrix is incomplete or the hook is dead.

Approach: import the parametric module, collect hook set per scenario class
from the class-level sets (PRIVATE_MODE_HOOKS, PRETOOL_AGENT_HOOKS,
POSTTOOL_EDIT_WRITE_HOOKS, HOOKS_NEEDING_PROJECT, JSON_HOOKS, TOOL_HOOKS,
NON_STDIN_HOOKS), then cross-check against the on-disk inventory.

The two "universal" scenarios are TestEmptyStdin (applies to every stdin hook)
and TestPrivateMode/TestToolNameFiltering/etc. that apply conditionally. Every
hook that receives stdin is covered by TestEmptyStdin — that is the floor.
Hooks that don't receive stdin (NON_STDIN_HOOKS) are covered by being
in that exempt set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.hooks import test_hook_graceful_degradation as gd

pytestmark = [pytest.mark.audit]


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOKS_DIR = PROJECT_ROOT / "hooks"


def _on_disk_hooks() -> set[str]:
    """Every .sh in hooks/ that is not a _lib helper."""
    return {p.name for p in HOOKS_DIR.glob("*.sh") if not p.name.startswith("_")}


def _hook_coverage_universe() -> set[str]:
    """Union of every hook referenced by any scenario in the parametric module.

    If a hook appears in NONE of these sets AND is not in NON_STDIN_HOOKS,
    it is either covered only by the parametric fixture (TestEmptyStdin) or
    not covered at all. The fixture itself pulls from _list_stdin_hooks(),
    so any on-disk stdin hook IS tested by TestEmptyStdin — the floor.
    """
    universe: set[str] = set()
    universe |= gd.NON_STDIN_HOOKS
    universe |= gd.PRIVATE_MODE_HOOKS
    universe |= gd.PRETOOL_AGENT_HOOKS
    universe |= gd.POSTTOOL_EDIT_WRITE_HOOKS
    universe |= gd.HOOKS_NEEDING_PROJECT
    universe |= gd.JSON_HOOKS
    universe |= set(gd.TOOL_HOOKS.keys())
    return universe


def test_parametric_module_discovers_hooks():
    """Sanity: the parametric module's discovery returns a non-empty set."""
    hooks = gd._list_hooks()
    assert len(hooks) >= 50, (
        f"Expected >=50 hooks from _list_hooks(), got {len(hooks)}. "
        f"Parametric matrix may have lost its discovery."
    )


def test_every_on_disk_hook_is_in_floor_matrix():
    """Every hook in hooks/ must be visible to the parametric matrix.

    _list_hooks() in the parametric file enumerates hooks/*.sh directly.
    That gives TestEmptyStdin/TestCompletelyEmptyStdin coverage for every
    stdin hook automatically. NON_STDIN_HOOKS are exempted by design.

    This test asserts the enumeration itself produces every file we expect.
    """
    on_disk = _on_disk_hooks()
    parametric_set = {h.name for h in gd._list_hooks()}

    missing_from_matrix = on_disk - parametric_set
    assert not missing_from_matrix, (
        f"{len(missing_from_matrix)} hook(s) exist in hooks/ but are not "
        f"discovered by the parametric matrix: {sorted(missing_from_matrix)}. "
        f"Fix _list_hooks() in test_hook_graceful_degradation.py."
    )


def test_non_stdin_hooks_exist_on_disk():
    """Every hook in NON_STDIN_HOOKS must actually exist.

    A stale entry there means a hook was renamed/removed but the exempt list
    wasn't updated — a dead exemption that could hide a real failure.
    """
    on_disk = _on_disk_hooks()
    # NON_STDIN_HOOKS can legitimately list hooks under packages/ too,
    # so accept a broader check.
    package_hooks: set[str] = set()
    for p in PROJECT_ROOT.glob("packages/*/hooks/*.sh"):
        package_hooks.add(p.name)
    valid_names = on_disk | package_hooks

    stale = gd.NON_STDIN_HOOKS - valid_names
    assert not stale, (
        f"NON_STDIN_HOOKS contains {len(stale)} name(s) with no hook on disk: "
        f"{sorted(stale)}. Remove stale entries or restore the missing hook."
    )


def test_scenario_classes_reference_only_existing_hooks():
    """Each class-level hook set must reference only real hooks.

    Catches drift where a hook is renamed/removed but its test-scenario
    membership is not updated — creating a permanent no-op assertion.
    """
    on_disk = _on_disk_hooks()
    package_hooks: set[str] = set()
    for p in PROJECT_ROOT.glob("packages/*/hooks/*.sh"):
        package_hooks.add(p.name)
    valid_names = on_disk | package_hooks

    buckets: dict[str, set[str]] = {
        "PRIVATE_MODE_HOOKS": gd.PRIVATE_MODE_HOOKS,
        "PRETOOL_AGENT_HOOKS": gd.PRETOOL_AGENT_HOOKS,
        "POSTTOOL_EDIT_WRITE_HOOKS": gd.POSTTOOL_EDIT_WRITE_HOOKS,
        "HOOKS_NEEDING_PROJECT": gd.HOOKS_NEEDING_PROJECT,
        "JSON_HOOKS": gd.JSON_HOOKS,
        "TOOL_HOOKS": set(gd.TOOL_HOOKS.keys()),
    }

    issues: dict[str, list[str]] = {}
    for name, bucket in buckets.items():
        stale = sorted(bucket - valid_names)
        if stale:
            issues[name] = stale

    assert not issues, (
        f"Scenario hook sets reference non-existent hooks: {issues}. "
        f"Remove stale entries or restore the missing hook files."
    )


def test_at_least_one_hook_per_scenario():
    """Every scenario bucket must be non-empty.

    If a scenario defines a test but its hook set is empty, every test in
    that class will skip — a dead scenario. Surface it.
    """
    buckets: dict[str, set] = {
        "PRIVATE_MODE_HOOKS": gd.PRIVATE_MODE_HOOKS,
        "PRETOOL_AGENT_HOOKS": gd.PRETOOL_AGENT_HOOKS,
        "POSTTOOL_EDIT_WRITE_HOOKS": gd.POSTTOOL_EDIT_WRITE_HOOKS,
        "HOOKS_NEEDING_PROJECT": gd.HOOKS_NEEDING_PROJECT,
        "JSON_HOOKS": gd.JSON_HOOKS,
        "TOOL_HOOKS": set(gd.TOOL_HOOKS.keys()),
    }
    empty = [name for name, bucket in buckets.items() if not bucket]
    assert not empty, (
        f"Scenario hook bucket(s) are empty: {empty}. Every test in those "
        f"classes will skip. Populate the set or delete the scenario."
    )
