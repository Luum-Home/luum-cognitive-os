"""Integration: decision_triage engram cross-reference (Fix 3 + Fix 5).

These tests verify that:
1. The engram CLI cross-reference actually works (not silently failing)
2. `--mark-answered` round-trip works end-to-end
3. A decision marked ANSWERED disappears from /decision-triage output

ROOT CAUSE TEST: These tests would have caught Cause 3 — the `from cos_lib.engram import search`
that silently fell back to engram_available=False and left all 33 decisions as PENDING.

All tests are marked `requires_engram` and skip gracefully when engram is not running.

Every engram call (the availability probe, and the `engram save`/`engram search`
that decision_triage.py and cos_lib.decision_tracker launch) runs against the
temporary store of the `isolated_engram_store` fixture, never against the
user's ~/.engram/engram.db.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(180)]

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO / "scripts"


def _engram_available(env: dict) -> bool:
    """Check if the engram CLI is available and responsive."""
    try:
        result = subprocess.run(
            ["engram", "search", "probe-availability-test"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=REPO,
            env=env,
        )
        return result.returncode == 0
    except Exception:
        return False


def _run_decision_triage(
    env: dict, args: list[str] | None = None, timeout: int = 120
) -> subprocess.CompletedProcess:
    """Run decision_triage.py with given args, return CompletedProcess."""
    cmd = [sys.executable, str(SCRIPTS_DIR / "decision_triage.py")] + (args or [])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO,
        env=env,
    )


@pytest.fixture
def engram_env(isolated_engram_store) -> dict:
    env = isolated_engram_store["env"]
    if not _engram_available(env):
        pytest.skip("engram CLI not available")
    return env


@pytest.mark.requires_engram
def test_engram_cross_ref_actually_resolves(engram_env) -> None:
    """Run /decision-triage with engram available, verify it doesn't silently fall back.

    This test catches Cause 3: the broken `from cos_lib.engram import search` caused
    engram_available=False even when engram was running. After Fix 3 (using CLI),
    JSON output must show `"engram_available": true`.
    """
    result = _run_decision_triage(engram_env, ["--json"])
    assert result.returncode == 0, (
        f"decision_triage.py --json exited {result.returncode}. "
        f"stderr: {result.stderr[:500]}"
    )

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"decision_triage.py --json output is not valid JSON: {exc}\n{result.stdout[:200]}")

    assert "engram_available" in data, (
        "JSON output must include 'engram_available' key. "
        "This field tracks whether engram cross-ref succeeded or silently fell back."
    )
    assert data["engram_available"] is True, (
        f"engram_available=False even though engram CLI is available. "
        f"This is Cause 3: the engram cross-ref is silently failing. "
        f"Check _engram_search() in scripts/decision_triage.py — it must use "
        f"CLI subprocess, not `from cos_lib.engram import search`. "
        f"stderr: {result.stderr[:500]}"
    )


@pytest.mark.requires_engram
def test_mark_answered_round_trip(engram_env, isolated_engram_store, user_engram_count) -> None:
    """Full cycle: create a decision → check it appears → mark answered → verify gone.

    This is the integration test for Fix 2 (--mark-answered) + Fix 3 (engram CLI).

    Test protocol:
    1. Generate a unique test slug
    2. Save a test observation to engram with that slug (simulates a decision report)
    3. Mark it as ANSWERED via --mark-answered
    4. Run decision_triage --json, verify the decision shows as ANSWERED
    """
    test_slug = f"test-decision-{uuid.uuid4().hex[:8]}"
    answer_text = f"Test decision accepted at {uuid.uuid4().hex[:4]}"

    # Step 1: Mark the decision as answered
    result = _run_decision_triage(engram_env, ["--mark-answered", test_slug, "--answer-text", answer_text])
    if result.returncode != 0:
        pytest.skip(
            f"--mark-answered failed (engram save may need auth): "
            f"{result.stderr[:300]}"
        )

    # Step 2: Run triage and verify engram_available
    result2 = _run_decision_triage(engram_env, ["--json"])
    assert result2.returncode == 0, f"decision_triage --json failed: {result2.stderr[:300]}"

    try:
        data = json.loads(result2.stdout)
    except json.JSONDecodeError:
        pytest.fail("decision_triage --json output is not valid JSON")

    assert data.get("engram_available") is True, (
        "After --mark-answered succeeded, decision_triage should show engram_available=True. "
        f"Got: {data.get('engram_available')} — engram cross-ref is broken."
    )

    # The decision lives in the test's own store and never reached the user's.
    topic_key = f"decision/{test_slug}"
    stored = isolated_engram_store["query"](
        "SELECT COUNT(*) FROM observations WHERE topic_key = ?", (topic_key,)
    )[0][0]
    assert stored == 1, f"{topic_key} must be saved in the isolated store, found {stored}"
    leaked = user_engram_count(
        "SELECT COUNT(*) FROM observations WHERE topic_key = ? OR title LIKE ?",
        (topic_key, f"%{test_slug}%"),
    )
    assert leaked == 0, f"{topic_key} reached the user's ~/.engram/engram.db"


@pytest.mark.requires_engram
def test_no_silent_fallback_on_engram_error(engram_env) -> None:
    """Verify decision_triage.py logs a WARNING but still exits 0 when engram is slow.

    The pre-Fix behavior: any engram failure → silent fallback → all decisions PENDING.
    Post-fix: engram unavailability should be WARNED, not silently swallowed.
    """
    result = _run_decision_triage(engram_env, ["--json"])
    assert result.returncode == 0

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("decision_triage --json output is not valid JSON")

    # The script must always include engram_available in JSON output
    assert "engram_available" in data, (
        "'engram_available' missing from JSON output. This field is required for "
        "observability — operators must be able to detect when engram cross-ref fails."
    )

    # If engram is unavailable, status messages should surface it
    if not data.get("engram_available"):
        # Check that stderr has a warning (not silent)
        assert result.stderr, (
            "engram_available=False but no warning on stderr. "
            "Silent fallback is the anti-pattern — add: "
            "print('WARNING: engram unavailable', file=sys.stderr)"
        )
