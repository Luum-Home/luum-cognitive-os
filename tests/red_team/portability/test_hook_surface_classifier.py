# SCOPE: os-only
"""Paired proof for scripts/hook_surface_classifier.py.

The classifier answers "what are the unregistered hooks?" by DESTINATION. The
value of that answer collapses in exactly two ways, so both are tested:

1. POPULATION GUARD — an empty scan must never read as a clean scan. If the
   classifier can return "0 unclassified" because it found no hooks at all, the
   green means nothing.
2. BITE — a hook that genuinely has no destination must land in `unclassified`,
   and a hook whose only destination is a written ledger must NOT be counted as
   reachable under the active configuration. Both are the cheap-green failures
   of this audit family: one hides dead surface, the other launders latent
   surface into live surface.

Plus the arithmetic the report rests on: buckets partition the population
exactly once, and `reachability` never counts a profile-gated hook as active.

Every test drives the module's own functions or its CLI. None asserts that a
file exists.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "hook_surface_classifier.py"


def _load():
    spec = importlib.util.spec_from_file_location("hook_surface_classifier", SCRIPT)
    assert spec and spec.loader, f"cannot load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hook_surface_classifier"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load()


@pytest.fixture(scope="module")
def report(mod):
    return mod.classify()


def test_population_is_not_empty(report):
    """Green-because-empty is the failure mode this guard refuses."""
    total = report["totals"]["hooks_on_disk"]
    assert total > 100, (
        f"only {total} hooks discovered; a scan this small means the inventory "
        "broke, and every downstream count is meaningless"
    )
    assert report["totals"]["registered"] > 0, "no registered hooks found at all"


def test_buckets_partition_the_population_exactly_once(mod, report):
    """Every hook lands in exactly one primary bucket, and none is dropped."""
    assert sum(report["buckets"].values()) == report["totals"]["hooks_on_disk"]
    assert set(report["buckets"]) == set(mod.BUCKET_ORDER)
    hooks = [r["hook"] for r in report["rows"]]
    assert len(hooks) == len(set(hooks)), "a hook was classified twice"


def test_reachability_splits_active_from_latent(report):
    """A hook reachable only under a non-active profile is NOT active surface.

    This is the launder: counting `full`-profile and security-profile hooks as
    live turns 181 running hooks into 257 and makes the surface look justified.
    """
    rc = report["reachability"]
    assert len(rc["active"]) + len(rc["latent"]) + len(rc["none"]) == report["totals"][
        "hooks_on_disk"
    ]
    latent = set(rc["latent"])
    by_name = {r["hook"]: r for r in report["rows"]}
    for name in latent:
        assert by_name[name]["bucket"] not in ("registered", "adr311_dispatch")
    for name in rc["active"]:
        assert by_name[name]["bucket"] in ("registered", "adr311_dispatch")


def test_unregistered_arithmetic_matches_the_inventory(report):
    t = report["totals"]
    assert t["registered"] + t["unregistered"] == t["hooks_on_disk"]
    counted = sum(1 for r in report["rows"] if r["bucket"] == "registered")
    assert counted == t["registered"]


def test_registry_files_are_never_treated_as_callers(mod):
    """Naming a hook in a bookkeeping list is not invoking it.

    hooks/_lib/registration-allowlist.txt names ~185 hooks. Before this
    exclusion it made 64 hooks look "delegated", which is precisely the weak
    evidence the audit exists to stop accepting.
    """
    assert "hooks/_lib/registration-allowlist.txt" in mod.REGISTRY_FILES
    names = {"adr-detector.sh", "agent-bus-monitor.sh"}
    hits = mod.scan_refs(names, ("hooks",), invocation_only=True)
    for name in names:
        assert "hooks/_lib/registration-allowlist.txt" not in hits[name]


def test_delegation_requires_an_invocation_shaped_line(mod):
    """A bare mention must not count; an execution must."""
    assert mod.INVOKE_RE.search('bash "$PROJECT_DIR/hooks/foo.sh"')
    assert mod.INVOKE_RE.search('subprocess.run(["hooks/foo.sh"])')
    assert not mod.INVOKE_RE.search("# see foo.sh for the rationale")
    assert not mod.INVOKE_RE.search("foo.sh")


def test_a_hook_with_no_destination_lands_in_unclassified(mod, report, monkeypatch):
    """BITE: plant a hook that nothing references and it must surface.

    Without this the audit could return `unclassified: 0` by construction, and
    a permanently-zero finding bucket is indistinguishable from a broken one.
    """
    names, resolved = mod.inventory()
    ghost = "zz-synthetic-orphan-hook.sh"
    monkeypatch.setattr(
        mod, "inventory", lambda: (names + [ghost], {**resolved, ghost: f"/x/{ghost}"})
    )
    planted = mod.classify()
    row = next(r for r in planted["rows"] if r["hook"] == ghost)
    assert row["bucket"] == "unclassified", (
        f"a hook with no settings entry, no dispatcher reference, no profile and "
        f"no ledger was classified as {row['bucket']}"
    )
    assert ghost in planted["reachability"]["none"]
    assert planted["buckets"]["unclassified"] == report["buckets"]["unclassified"] + 1


def test_ledger_coverage_is_measured_not_assumed(report):
    """The classification manifest's own contract line is checkable, so check it.

    manifests/hook-registration-classification.yaml states: "Every unregistered
    top-level hook must appear here". `unregistered_in_no_ledger` is the
    measurement of that claim, and it is allowed to be non-empty -- but it must
    be REPORTED, and the exit code must reflect it.
    """
    lg = report["ledgers"]
    assert isinstance(lg["unregistered_in_no_ledger"], list)
    assert lg["registration-allowlist"] > 0
    assert lg["EXCLUDED_HOOKS"] > 0


def test_ratchet_slack_is_reported(report):
    """A suppressor that suppresses nothing must be visible, not silent.

    The allowlist header promises the list only shrinks. Entries for hooks that
    are now registered, or that have no file at all, are free seats: the gate
    reports "intentionally unregistered" over hooks that are neither.
    """
    rt = report["ratchet"]
    assert rt["entries"] == len(rt["live"]) + len(rt["stale_now_registered"]) + len(
        rt["stale_no_file"]
    )
    assert isinstance(rt["stale_now_registered"], list)


def test_cli_json_is_parseable_and_exit_code_signals_findings():
    """Contract: 0 = nothing to look at, 1 = findings, 2 = error."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode in (0, 1), f"unexpected exit {proc.returncode}: {proc.stderr}"
    data = json.loads(proc.stdout)
    has_findings = bool(
        data["buckets"]["unclassified"] or data["ledgers"]["unregistered_in_no_ledger"]
    )
    assert proc.returncode == (1 if has_findings else 0)


def test_lib_and_archived_are_excluded_from_the_hook_population(mod):
    """hooks/_lib/ holds sourced libraries, not hooks.

    Counting the 34 files under _lib as "unregistered hooks" is the arithmetic
    that turns 103 into 137, and 34 shell libraries are not missing telemetry.
    """
    names, _ = mod.inventory()
    assert not any("/" in n for n in names)
    lib = REPO_ROOT / "hooks" / "_lib"
    if lib.is_dir():
        lib_names = {p.name for p in lib.glob("*.sh")}
        assert lib_names, "fixture assumption broken: hooks/_lib has no .sh files"
        assert not (lib_names & set(names))
