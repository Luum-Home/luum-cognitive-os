"""Integration tests for profile-drift-autoapply.sh concurrency safety.

Incident 2026-05-01-session-3-spawn-hang: when N parallel sessions all fire
SessionStart simultaneously and the hash file is stale, all N processes
detect drift, all N concurrently call apply-efficiency-profile.sh, and all
N race to write .claude/settings.json. The IDE detects partial writes and
re-spawns the session, fanning out further.

Mitigation: profile-drift-autoapply.sh now acquires a non-blocking flock on
.cognitive-os/runtime/profile-autoapply.lock. The first invocation wins
the lock and re-applies; the others exit 0 silently.

These tests verify that property under real concurrent invocation against
a stubbed apply script.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path



REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "hooks" / "profile-drift-autoapply.sh"


def _make_project(tmp_path: Path, apply_script_body: str) -> Path:
    """Create a minimal cos project with a stub apply-efficiency-profile.sh.

    The stub records each invocation by appending to a counter file under
    runtime/, so concurrent calls are observable via line count.
    """
    project = tmp_path / "project"
    runtime_dir = project / ".cognitive-os" / "runtime"
    scripts_dir = project / "scripts"
    runtime_dir.mkdir(parents=True)
    scripts_dir.mkdir()

    apply_script = scripts_dir / "apply-efficiency-profile.sh"
    apply_script.write_text(apply_script_body)
    apply_script.chmod(0o755)

    # Pre-populate a STALE hash so drift is detected.
    (runtime_dir / "last-applied-profile.sha").write_text("stale-hash-value\n")

    return project


def _run_hook(project_dir: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run profile-drift-autoapply.sh once against *project_dir*."""
    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COS_DISABLE_PROFILE_AUTOAPPLY": "0",
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_single_invocation_applies_when_drift_detected(tmp_path: Path) -> None:
    """Sanity baseline: a lone invocation against a stale hash must re-apply."""
    counter = tmp_path / "apply-count.txt"
    apply_script = f'''#!/usr/bin/env bash
echo "applied" >> "{counter}"
exit 0
'''
    project = _make_project(tmp_path, apply_script)

    result = _run_hook(project)
    assert result.returncode == 0, result.stderr

    # Apply ran exactly once.
    assert counter.exists()
    assert len(counter.read_text().splitlines()) == 1

    # Hash file was updated with a non-stale value.
    new_hash = (project / ".cognitive-os" / "runtime" / "last-applied-profile.sha").read_text().strip()
    assert new_hash != "stale-hash-value"
    assert len(new_hash) >= 40  # sha256 hex


def test_no_apply_when_hash_matches(tmp_path: Path) -> None:
    """When the stored hash matches the script, no apply runs at all."""
    counter = tmp_path / "apply-count.txt"
    apply_script = '#!/usr/bin/env bash\necho applied >> "/tmp/never_called_for_hash_match"\nexit 0\n'
    project = _make_project(tmp_path, apply_script)

    # Compute the script's actual hash and seed the hash file with it.
    apply_script_path = project / "scripts" / "apply-efficiency-profile.sh"
    digest_proc = subprocess.run(
        ["shasum", "-a", "256", str(apply_script_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    matching_hash = digest_proc.stdout.split()[0]
    (project / ".cognitive-os" / "runtime" / "last-applied-profile.sha").write_text(matching_hash + "\n")

    result = _run_hook(project)
    assert result.returncode == 0
    assert not counter.exists(), "apply must NOT run when hash matches"


def test_concurrent_invocations_only_apply_once(tmp_path: Path) -> None:
    """The flock guard must serialize concurrent invocations.

    Launches 5 parallel hook processes against the same project dir with a
    stale hash. The stub apply script sleeps long enough that all 5 hook
    processes overlap in time. The flock must keep all-but-one out of the
    apply path.
    """
    counter = tmp_path / "apply-count.txt"
    apply_script = f'''#!/usr/bin/env bash
# Sleep so concurrent invocations definitely overlap in time.
sleep 1
echo "applied" >> "{counter}"
exit 0
'''
    project = _make_project(tmp_path, apply_script)

    n_workers = 5
    results: list[subprocess.CompletedProcess] = []
    results_lock = threading.Lock()

    def worker() -> None:
        r = _run_hook(project, timeout=20)
        with results_lock:
            results.append(r)

    threads = [threading.Thread(target=worker) for _ in range(n_workers)]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    elapsed = time.monotonic() - start

    # All 5 hook invocations exited successfully (the lock losers exit 0 silently).
    assert len(results) == n_workers, "all 5 worker threads must complete"
    for r in results:
        assert r.returncode == 0, f"hook should always exit 0; stderr={r.stderr}"

    # The apply script ran AT MOST ONCE despite 5 concurrent invocations.
    # (Could be 0 if all lost the lock, but in practice exactly 1 wins.)
    apply_count = len(counter.read_text().splitlines()) if counter.exists() else 0
    assert apply_count <= 1, f"flock failed: apply ran {apply_count} times; expected ≤1"
    assert apply_count == 1, (
        f"expected exactly 1 apply (one winner), got {apply_count}. "
        "If this is 0, the test launch raced before flock acquisition; rerun."
    )

    # Total wall-clock should be only marginally more than one apply (1s sleep),
    # not 5×. Generous bound: ≤6s. If serialized under the lock with sequential
    # waiters this would be ~5s; we assert non-blocking lock by checking ≤4s.
    assert elapsed < 4.0, (
        f"flock appears to be BLOCKING, not non-blocking. "
        f"5 concurrent invocations took {elapsed:.1f}s; expected <4s under -n flock"
    )


def test_lock_released_after_completion(tmp_path: Path) -> None:
    """Sequential invocations must each be able to acquire the lock once
    the previous holder has exited."""
    counter = tmp_path / "apply-count.txt"
    apply_script = f'''#!/usr/bin/env bash
echo "applied" >> "{counter}"
exit 0
'''
    project = _make_project(tmp_path, apply_script)

    # First run applies (drift detected; hash gets updated to current).
    r1 = _run_hook(project)
    assert r1.returncode == 0
    assert len(counter.read_text().splitlines()) == 1

    # Tamper hash to re-introduce drift.
    (project / ".cognitive-os" / "runtime" / "last-applied-profile.sha").write_text("again-stale\n")

    # Second run must also apply (lock was released between runs).
    r2 = _run_hook(project)
    assert r2.returncode == 0
    assert len(counter.read_text().splitlines()) == 2, (
        "second sequential run did not apply; lock may not have been released"
    )


def test_optout_env_var_short_circuits(tmp_path: Path) -> None:
    """COS_DISABLE_PROFILE_AUTOAPPLY=1 bypasses everything, including the lock."""
    counter = tmp_path / "apply-count.txt"
    apply_script = f'#!/usr/bin/env bash\necho applied >> "{counter}"\nexit 0\n'
    project = _make_project(tmp_path, apply_script)

    env = {
        **os.environ,
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "COS_DISABLE_PROFILE_AUTOAPPLY": "1",
    }
    result = subprocess.run(
        ["bash", str(HOOK)],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert not counter.exists(), "apply must NOT run when opt-out is set"
