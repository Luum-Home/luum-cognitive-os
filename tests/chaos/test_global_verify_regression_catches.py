"""ADR-027 Phase 1 — Chaos test: global-verify.sh blocks regressions end-to-end.

Scenario:
  1. Create a passing test in a tmp dir.
  2. Invoke `bash hooks/global-verify.sh before` with the test in the resolver.
  3. Modify the test so it *fails*.
  4. Invoke `bash hooks/global-verify.sh after`.
  5. Assert exit 1 (BLOCKED) + "BLOCKER" in stderr.
  6. Assert the verify-events.jsonl contains a `verify.after.compared` event
     with delta_failed > 0.

This exercises the entire hook end-to-end: baseline capture → regression
detection → metric emission → non-zero exit (the blocking signal).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

_PROJ_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOK = _PROJ_ROOT / "hooks" / "global-verify.sh"
_RESOLVER_PATH = _PROJ_ROOT / "lib" / "targeted_test_resolver.py"

pytestmark = pytest.mark.skipif(
    not _HOOK.exists(), reason="hooks/global-verify.sh not found"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResolver:
    """Temporarily replace lib/targeted_test_resolver.py with a fake one."""

    def __init__(self, test_ids: list[str]):
        self._test_ids = test_ids
        self._existed = _RESOLVER_PATH.exists()
        self._original: bytes | None = None

    def update(self, test_ids: list[str]) -> None:
        """Update the fake resolver to return different test IDs."""
        self._write(test_ids)

    def _write(self, test_ids: list[str]) -> None:
        code = "def resolve_tests_for_changes(files):\n    return " + repr(test_ids) + "\n"
        _RESOLVER_PATH.write_text(code, encoding="utf-8")

    def __enter__(self) -> "_FakeResolver":
        if self._existed:
            self._original = _RESOLVER_PATH.read_bytes()
        self._write(self._test_ids)
        return self

    def __exit__(self, *_) -> None:
        if self._existed and self._original is not None:
            _RESOLVER_PATH.write_bytes(self._original)
        elif not self._existed:
            _RESOLVER_PATH.unlink(missing_ok=True)


def _run_hook(mode: str, agent_id: str, project_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["AGENT_ID"] = agent_id
    # This chaos test intentionally exercises the legacy resolver path. In the
    # SO repo, global-verify defaults to cos-test focused and only allows the
    # legacy resolver through an explicit compatibility flag.
    env["COS_GLOBAL_VERIFY_ALLOW_LEGACY_RESOLVER"] = "1"
    env["VERIFY_FILES_OVERRIDE"] = "lib/synthetic_changed_for_chaos.py"
    # Ensure killswitch is NOT set (we want the hook to run fully)
    env.pop("COGNITIVE_OS_KILLSWITCH", None)
    return subprocess.run(
        ["bash", str(_HOOK), mode],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        cwd=str(_PROJ_ROOT),
    )


# ---------------------------------------------------------------------------
# Main scenario
# ---------------------------------------------------------------------------


def test_global_verify_catches_regression(tmp_path: Path) -> None:
    """End-to-end: passing baseline → introduce failure → after-phase blocks."""
    agent_id = "chaos-regression-test"

    # Set up metrics/baseline dirs under the REAL project dir (hook uses COGNITIVE_OS_PROJECT_DIR)
    baseline_dir = _PROJ_ROOT / ".cognitive-os" / "runtime" / "verify-baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_file = baseline_dir / f"{agent_id}.json"
    metrics_dir = _PROJ_ROOT / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    verify_events = metrics_dir / "verify-events.jsonl"

    # Create a test file that PASSES initially
    test_file = tmp_path / "test_chaos_regression.py"
    test_file.write_text("def test_passes():\n    assert True\n", encoding="utf-8")
    test_path = str(test_file)

    # Clean up any leftover baseline from previous runs
    baseline_file.unlink(missing_ok=True)

    # Record the line count of verify-events.jsonl before the test
    events_before = verify_events.read_text(encoding="utf-8").splitlines() if verify_events.exists() else []

    with _FakeResolver([test_path]):
        # Step 1: run 'before' phase — should capture passing baseline
        before_result = _run_hook("before", agent_id, _PROJ_ROOT)
        assert before_result.returncode == 0, (
            f"'before' phase should exit 0.\nstderr: {before_result.stderr}\n"
            f"stdout: {before_result.stdout}"
        )
        assert baseline_file.exists(), (
            "Baseline file must be written by 'before' phase."
        )
        baseline_data = json.loads(baseline_file.read_text(encoding="utf-8"))
        # Baseline must not be skipped (we provided a real test)
        assert not baseline_data.get("skipped"), (
            f"Baseline should not be skipped; got: {baseline_data}"
        )

        # Step 2: modify the test so it FAILS
        test_file.write_text(
            "def test_now_failing():\n    assert False, 'chaos regression introduced'\n",
            encoding="utf-8",
        )

        # Step 3: run 'after' phase — should detect regression and exit 1
        after_result = _run_hook("after", agent_id, _PROJ_ROOT)

        assert after_result.returncode == 1, (
            f"'after' phase must exit 1 (regression detected), got {after_result.returncode}.\n"
            f"stderr: {after_result.stderr}\nstdout: {after_result.stdout}"
        )
        assert "BLOCKER" in after_result.stderr, (
            f"'BLOCKER' must appear in stderr.\nstderr: {after_result.stderr}"
        )

    # Baseline file should be cleaned up by the 'after' phase
    assert not baseline_file.exists(), (
        "Baseline file must be removed after 'after' phase."
    )

    # Step 4: verify that a verify.after.compared MetricEvent with delta_failed > 0 was emitted
    assert verify_events.exists(), (
        f"verify-events.jsonl must be written by the hook.\nExpected at: {verify_events}"
    )
    events_after = verify_events.read_text(encoding="utf-8").splitlines()
    new_events = events_after[len(events_before):]
    assert new_events, "At least one new event must be appended to verify-events.jsonl."

    # Find the verify.after.compared event
    compared_events = []
    for line in new_events:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("event_type") == "verify.after.compared":
            compared_events.append(ev)

    assert compared_events, (
        f"Expected a 'verify.after.compared' event in verify-events.jsonl.\n"
        f"New events written:\n" + "\n".join(new_events[:10])
    )

    event = compared_events[-1]
    payload = event.get("payload", {})
    delta_failed = payload.get("delta_failed", 0)
    assert delta_failed > 0, (
        f"delta_failed must be > 0 in the verify.after.compared event.\n"
        f"Full event: {json.dumps(event, indent=2)}"
    )
    assert payload.get("regression") is True, (
        f"'regression' must be True in the event payload.\nPayload: {payload}"
    )
