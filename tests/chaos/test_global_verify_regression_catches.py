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
    """Provide a fake targeted_test_resolver via VERIFY_RESOLVER_DIR injection.

    ADR-238 Bug 5 fix: the previous implementation overwrote the real
    ``lib/targeted_test_resolver.py`` in the repo on disk, which corrupted
    production source code if the test was interrupted between ``__enter__``
    and ``__exit__`` (or if the original file did not exist when the test
    started). The hook supports a ``VERIFY_RESOLVER_DIR`` env var (5th arg
    to the embedded python) that prepends a directory to ``sys.path`` so a
    test-local ``lib/targeted_test_resolver.py`` is imported instead. We
    write the fake under a caller-provided temp directory and expose the
    path via :pyattr:`resolver_dir` so callers can set the env var.
    """

    def __init__(self, test_ids: list[str], tmp_root: Path):
        self._test_ids = test_ids
        # Per-instance dedicated subtree so concurrent chaos tests don't clash.
        self._root = tmp_root / "fake_resolver_root"
        self._lib_dir = self._root / "lib"
        self._resolver_path = self._lib_dir / "targeted_test_resolver.py"

    @property
    def resolver_dir(self) -> Path:
        return self._root

    def update(self, test_ids: list[str]) -> None:
        """Update the fake resolver to return different test IDs."""
        self._write(test_ids)

    def _write(self, test_ids: list[str]) -> None:
        self._lib_dir.mkdir(parents=True, exist_ok=True)
        # Make ``lib`` a package so ``from lib.targeted_test_resolver import ...``
        # resolves through this directory before the real source tree.
        init_py = self._lib_dir / "__init__.py"
        if not init_py.exists():
            init_py.write_text("", encoding="utf-8")
        code = "def resolve_tests_for_changes(files):\n    return " + repr(test_ids) + "\n"
        self._resolver_path.write_text(code, encoding="utf-8")

    def __enter__(self) -> "_FakeResolver":
        # Sanity guard: never let this helper touch the real source file.
        assert _RESOLVER_PATH.resolve() != self._resolver_path.resolve(), (
            "Fake resolver path must not collide with real lib/targeted_test_resolver.py"
        )
        self._write(self._test_ids)
        return self

    def __exit__(self, *_) -> None:
        # Tmp dir is cleaned up by pytest's tmp_path fixture; nothing to do.
        return None


def _run_hook(mode: str, agent_id: str, project_dir: Path, resolver_dir: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["AGENT_ID"] = agent_id
    # This chaos test intentionally exercises the legacy resolver path. In the
    # SO repo, global-verify defaults to cos-test focused and only allows the
    # legacy resolver through an explicit compatibility flag.
    env["COS_GLOBAL_VERIFY_ALLOW_LEGACY_RESOLVER"] = "1"
    env["VERIFY_FILES_OVERRIDE"] = "lib/synthetic_changed_for_chaos.py"
    if resolver_dir is not None:
        # ADR-238 Bug 5: inject a per-test resolver directory; the hook prepends
        # this to sys.path before importing lib.targeted_test_resolver so we do
        # not have to mutate the real source file on disk.
        env["VERIFY_RESOLVER_DIR"] = str(resolver_dir)
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

    # Snapshot the real resolver bytes so we can FAIL LOUDLY if the test ever
    # corrupts production source code again (ADR-238 Bug 5 defense-in-depth).
    real_resolver_before = _RESOLVER_PATH.read_bytes() if _RESOLVER_PATH.exists() else None

    with _FakeResolver([test_path], tmp_path) as fake:
        # Step 1: run 'before' phase — should capture passing baseline
        before_result = _run_hook("before", agent_id, _PROJ_ROOT, resolver_dir=fake.resolver_dir)
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
        after_result = _run_hook("after", agent_id, _PROJ_ROOT, resolver_dir=fake.resolver_dir)

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

    # ADR-238 Bug 5 guard: ensure the real lib/targeted_test_resolver.py was NOT
    # mutated by this chaos test. If this fires, we have regressed back to the
    # source-corrupting behavior.
    real_resolver_after = _RESOLVER_PATH.read_bytes() if _RESOLVER_PATH.exists() else None
    assert real_resolver_after == real_resolver_before, (
        "Real lib/targeted_test_resolver.py was modified by the chaos test. "
        "This is the ADR-238 Bug 5 escape: tests must not write to production source files."
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
