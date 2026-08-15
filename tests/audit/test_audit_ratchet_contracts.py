"""Run the ratcheted census scripts and assert the contract each one measures.

These five audits were written on 2026-08-15 and left unwired: each ships a
baseline or ratchet manifest, but nothing invoked it, so the ratchet could only
ever be read by a human who remembered it existed. This module is the consumer.

Deliberate design note — these tests execute the census and assert its
FINDINGS, never its importability. ``scripts/aspirational_audit.py`` promotes a
script from DORMANT to ON_DEMAND on the mere existence of a covering test, so a
test that only proved ``import`` works would turn the meter green while leaving
the audit as dead as it was. Every assertion below reads a number the census
produced, and every one of them fails if the census stops measuring (the
``population``/``total`` guards catch an audit that silently walks zero files
and reports a clean sheet).

Ratchets are read from the audit's own output, not restated here, so this file
can never disagree with the manifest. The direction is one-way: findings may
shrink, never grow. Raising a baseline to quiet a red is the failure mode these
manifests exist to prevent.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> tuple[int, dict]:
    """Execute a census script and return (exit code, parsed JSON payload)."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / script), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic path
        pytest.fail(f"{script} emitted non-JSON on stdout: {exc}\nstderr:\n{proc.stderr}")
    return proc.returncode, payload


# --------------------------------------------------------------------------
# scripts/audit_adopt_verdict_linkage.py — ratchet 8 unlinked / 0 dangling
# --------------------------------------------------------------------------


def test_adopt_verdict_linkage_holds_its_ratchet() -> None:
    code, payload = _run("audit_adopt_verdict_linkage.py", "--json")

    # The census must actually have walked something.
    assert payload["population"] > 0, "adopt-verdict census walked an empty population"

    ratchet = payload["ratchet"]
    assert payload["unlinked"] <= ratchet["unlinked"], (
        f"unlinked adopt verdicts regressed: {payload['unlinked']} > ratchet "
        f"{ratchet['unlinked']}. Link the verdict to its ADR; do not raise the ratchet."
    )
    # Dangling ADR references are pinned at zero: a verdict citing an ADR that
    # does not exist is always a defect, never accepted debt.
    assert payload["dangling"] <= ratchet["dangling"], (
        f"dangling ADR references appeared: {payload['dangling']} > "
        f"{ratchet['dangling']}. A verdict cites an ADR that is not in the repo."
    )
    assert code == 0, "audit exits non-zero while within ratchet"


# --------------------------------------------------------------------------
# scripts/audit_adr_path_reality.py — baseline manifest, exact-match ratchet
# --------------------------------------------------------------------------


def test_adr_path_reality_baseline_is_not_a_cushion() -> None:
    """Phantom-path count must equal its baseline: above fails, below is a cushion.

    This audit is stricter than a normal ratchet on purpose. ``count > baseline``
    is a regression, and ``count < baseline`` is an ERROR (exit 2), because a
    baseline sitting above the measurement silently accepts new debt up to the
    gap. Both directions are asserted here so neither can drift unnoticed.
    """
    code, payload = _run("audit_adr_path_reality.py", "--json")

    assert payload["stats"]["adrs_scanned"] > 0, "ADR path census scanned zero ADRs"
    assert payload["stats"]["path_claims"] > 0, "census found no path claims at all"

    baseline = payload["baseline"]
    count = len(payload["findings"])
    assert baseline is not None, "manifests/adr-path-reality-baseline.json is missing"

    assert count <= baseline, (
        f"phantom ADR paths regressed: {count} > baseline {baseline}. "
        f"Fix the ADR path claim; do not raise the baseline."
    )
    assert count == baseline, (
        f"baseline {baseline} sits above reality {count} -- that gap is a cushion "
        f"that accepts {baseline - count} new phantom paths silently. "
        f"Re-run with --write-baseline to ratchet it down."
    )
    assert code == 0


# --------------------------------------------------------------------------
# scripts/audit_decision_backing.py — manifests/decision-backing-ratchet.yaml
# --------------------------------------------------------------------------


def test_decision_backing_reports_no_ratchet_regression() -> None:
    code, payload = _run("audit_decision_backing.py", "--json")

    assert payload["adr_files"] > 0, "decision-backing census read zero ADR files"
    assert payload["rows"], "decision-backing census produced no rows"

    # Each governed kind must stay at or below its recorded limit.
    for kind, c in payload["counts"].items():
        assert c["population"] > 0, f"kind {kind!r} has an empty population"
        assert c["unbacked"] <= c["limit"], (
            f"{kind}: {c['unbacked']} unbacked > limit {c['limit']}. "
            f"Cite the ADR; do not raise the limit."
        )

    assert payload["regressions"] == [], (
        f"decision-backing ratchet regressions: {payload['regressions']}"
    )
    assert code == 0


# --------------------------------------------------------------------------
# scripts/scope_closure_gate.py — manifests/scope-closure-baseline.yaml
# --------------------------------------------------------------------------


def test_scope_closure_gate_holds_its_baseline() -> None:
    code, payload = _run("scope_closure_gate.py", "--json")

    assert payload["closure_size"] > 0, "scope closure computed an empty closure"
    assert payload["seed_hooks"] > 0, "scope closure started from zero seed hooks"

    baseline = payload["baseline"]
    counts = payload["counts"]
    for kind, limit in baseline.items():
        got = counts.get(kind, 0)
        assert got <= limit, (
            f"scope-closure {kind}: {got} > baseline {limit}. "
            f"Fix the scope marker; do not raise the baseline."
        )
    assert code == 0


# --------------------------------------------------------------------------
# scripts/volatile_number_audit.py — manifests/volatile-number-baseline.json
# --------------------------------------------------------------------------


def test_volatile_number_audit_admits_no_new_debt() -> None:
    code, payload = _run("volatile_number_audit.py", "--format", "json")

    assert payload["totals"]["findings"] > 0, "volatile-number census found nothing at all"
    assert payload["totals"]["files"] > 0, "volatile-number census read zero files"

    assert payload["new_volatile"] == [], (
        f"new volatile numbers in prose (not baselined): {payload['new_volatile'][:5]}"
    )
    # A baseline entry that matches nothing is a suppressor suppressing nothing:
    # it is indistinguishable from cover for debt that no longer exists.
    assert payload["stale_baseline_entries"] == [], (
        f"stale baseline entries suppress nothing: {payload['stale_baseline_entries'][:5]}"
    )
    assert code == 0
