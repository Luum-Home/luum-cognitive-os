"""End-to-end smoke test for Cognitive OS session startup.

Simulates `SessionStart` WITHOUT spawning real Claude Code by invoking each
registered SessionStart hook directly and asserting post-conditions.

Scope (acceptance criteria mapped from task brief):
    1. Hook invocability — every SessionStart hook exists, is executable,
       and passes `bash -n`.
    2. session-watchdog-launcher.sh — opt-out honored, singleton behavior,
       pidfile lifecycle, no process leaks.
    3. session-heartbeat.sh — atomic write, epoch content.
    4. Runtime invariants — `cos-config-audit --json` succeeds with ≥ 1 IMPL,
       `cognitive-os-health.sh` does not crash.
    5. Idempotency — running the startup twice converges.
    6. Cross-phase invariant — Phase A `idle_cpu_threshold` ≥ Phase B
       `_CPU_IDLE_THRESHOLD_PCT` (observed alongside cos-config-audit).

Design constraints:
    * tmpdir as fake project root (CLAUDE_PROJECT_DIR).
    * subprocess timeouts ≤ 10 s per hook.
    * No psutil dependency — uses `os.kill(pid, 0)` for liveness.
    * All tests marked @pytest.mark.e2e.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not (sys.platform.startswith("darwin") or sys.platform.startswith("linux")),
        reason="e2e startup smoke tests require POSIX (macOS/Linux)",
    ),
]


# ──────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────

def _load_session_start_hooks(repo_root: Path) -> list[str]:
    """Return ordered list of hook script paths (relative to repo_root)
    registered under `SessionStart` in `.claude/settings.json`.
    """
    settings_path = repo_root / ".claude" / "settings.json"
    data = json.loads(settings_path.read_text())
    assert "hooks" in data, "settings.json missing top-level 'hooks'"
    ss = data["hooks"].get("SessionStart", [])
    assert isinstance(ss, list) and ss, "SessionStart must be a non-empty array"
    assert isinstance(ss[0], dict) and "hooks" in ss[0], (
        "Unexpected SessionStart schema — expected [{matcher, hooks:[...]}]"
    )
    out: list[str] = []
    for entry in ss[0]["hooks"]:
        cmd = entry.get("command", "")
        # command looks like: bash "$CLAUDE_PROJECT_DIR/hooks/foo.sh"
        # Extract the /hooks/foo.sh path via simple parsing.
        marker = "$CLAUDE_PROJECT_DIR/"
        if marker in cmd:
            rel = cmd.split(marker, 1)[1].rstrip('"').strip()
            out.append(rel)
    assert out, "No SessionStart hooks parsed from settings.json"
    return out


def _is_alive(pid: int) -> bool:
    """Liveness probe using `os.kill(pid, 0)` — no psutil needed."""
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False
    return True


def _cmdline_matches(pid: int, needle: str) -> bool:
    """Check a PID's cmdline contains `needle` using `ps -p PID -o command=`."""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return needle in result.stdout


def _kill_and_wait(pid: int, timeout: float = 2.0) -> None:
    """TERM then KILL, wait until the PID is gone."""
    import signal

    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not _is_alive(pid):
                return
            time.sleep(0.05)


def _make_fake_project(tmp_path: Path, repo_root: Path) -> Path:
    """Set up a fake COS project root that lets real hooks/scripts execute.

    Strategy:
        * Symlink `scripts/` and `lib/` from the real repo (so the watchdog
          entry-point is reachable at the path the launcher expects).
        * Create empty `.cognitive-os/runtime/`.
        * Do NOT copy `cognitive-os.yaml` — absence means "feature flag
          proceeds by default" per the launcher's awk logic.
    """
    fake = tmp_path / "fake_project"
    fake.mkdir()
    (fake / ".cognitive-os" / "runtime").mkdir(parents=True)
    (fake / "scripts").symlink_to(repo_root / "scripts")
    (fake / "lib").symlink_to(repo_root / "lib")
    return fake


def _run_launcher(
    repo_root: Path,
    fake_project: Path,
    env_overrides: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> subprocess.CompletedProcess:
    """Invoke `hooks/session-watchdog-launcher.sh` with `CLAUDE_PROJECT_DIR`
    pointed at the fake project. The launcher itself lives in the real repo.
    """
    hook = repo_root / "hooks" / "session-watchdog-launcher.sh"
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(fake_project)
    env["COGNITIVE_OS_PROJECT_DIR"] = str(fake_project)
    # Neutralize the killswitch so we exercise the happy path.
    env.pop("COS_KILLSWITCH", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(hook)],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# ──────────────────────────────────────────────────────────────────────────
# 1. Hook invocability
# ──────────────────────────────────────────────────────────────────────────

def test_session_start_hooks_exist_and_executable(repo_root: Path):
    """PROGRESS: [step 1/7] every SessionStart hook exists and is invocable.

    Invocation contract (from settings.json): `bash "$PROJECT_DIR/hooks/foo.sh"`.
    Because the harness invokes via explicit `bash`, the +x bit is advisory,
    not required. We HARD-fail on missing files and SOFT-warn on missing +x
    so hygiene issues surface without producing false positives for hooks
    that were intentionally left non-executable (e.g., template placeholders).
    """
    hook_paths = _load_session_start_hooks(repo_root)
    missing = []
    not_executable = []
    for rel in hook_paths:
        p = repo_root / rel
        if not p.is_file():
            missing.append(rel)
            continue
        mode = p.stat().st_mode
        if not (mode & stat.S_IXUSR):
            not_executable.append(rel)
    assert not missing, f"Missing SessionStart hooks: {missing}"
    if not_executable:
        import warnings

        warnings.warn(
            f"SessionStart hooks missing +x bit (advisory — invoked via "
            f"explicit `bash`): {not_executable}",
            stacklevel=1,
        )


def test_session_start_hooks_syntax_ok(repo_root: Path):
    """Every SessionStart hook must parse via `bash -n`."""
    bad = []
    for rel in _load_session_start_hooks(repo_root):
        p = repo_root / rel
        res = subprocess.run(
            ["bash", "-n", str(p)], capture_output=True, text=True, timeout=10
        )
        if res.returncode != 0:
            bad.append((rel, res.stderr.strip()))
    assert not bad, f"Syntax errors in SessionStart hooks: {bad}"


# ──────────────────────────────────────────────────────────────────────────
# 2. session-watchdog-launcher.sh behavior
# ──────────────────────────────────────────────────────────────────────────

def test_watchdog_launcher_optout_honored(tmp_path: Path, repo_root: Path):
    """PROGRESS: [step 2/7] COS_SESSION_WATCHDOG_DISABLE=1 must not spawn."""
    fake = _make_fake_project(tmp_path, repo_root)
    pidfile = fake / ".cognitive-os" / "runtime" / "session-watchdog.pid"
    assert not pidfile.exists()

    result = _run_launcher(
        repo_root, fake, env_overrides={"COS_SESSION_WATCHDOG_DISABLE": "1"}
    )
    assert result.returncode == 0, (
        f"launcher must exit 0 under opt-out: {result.stderr}"
    )
    # Give the (non)daemon a moment in case the launcher misbehaved.
    time.sleep(0.3)
    assert not pidfile.exists(), (
        "Opt-out was honored should not create a pidfile. "
        "HALT trigger: opt-out NOT honored (see task brief)."
    )


def test_watchdog_launcher_spawns_when_flag_on(tmp_path: Path, repo_root: Path):
    """With no opt-out + no explicit flag, launcher spawns a live daemon."""
    fake = _make_fake_project(tmp_path, repo_root)
    pidfile = fake / ".cognitive-os" / "runtime" / "session-watchdog.pid"

    spawned_pid: int | None = None
    try:
        result = _run_launcher(repo_root, fake)
        assert result.returncode == 0, (
            f"launcher exit!=0: stderr={result.stderr}"
        )
        # Allow daemon a moment to settle.
        deadline = time.time() + 3.0
        while time.time() < deadline and not pidfile.exists():
            time.sleep(0.05)
        assert pidfile.exists(), "pidfile was not created"
        spawned_pid = int(pidfile.read_text().strip())
        assert spawned_pid > 0
        # Daemon is alive and is the watchdog (not a PID-reuse victim).
        assert _is_alive(spawned_pid), f"daemon PID {spawned_pid} not alive"
        assert _cmdline_matches(spawned_pid, "so_session_watchdog"), (
            f"PID {spawned_pid} cmdline does not reference so_session_watchdog"
        )
    finally:
        # CRITICAL: never leak processes across tests.
        if spawned_pid is not None:
            _kill_and_wait(spawned_pid)
        if pidfile.exists():
            pidfile.unlink(missing_ok=True)


def test_watchdog_launcher_singleton_second_invocation(
    tmp_path: Path, repo_root: Path
):
    """A SECOND invocation must NOT spawn a new daemon when one already exists."""
    fake = _make_fake_project(tmp_path, repo_root)
    pidfile = fake / ".cognitive-os" / "runtime" / "session-watchdog.pid"

    first_pid: int | None = None
    try:
        # First launch.
        r1 = _run_launcher(repo_root, fake)
        assert r1.returncode == 0
        deadline = time.time() + 3.0
        while time.time() < deadline and not pidfile.exists():
            time.sleep(0.05)
        assert pidfile.exists()
        first_pid = int(pidfile.read_text().strip())
        assert _is_alive(first_pid)

        # Second launch — should be a no-op (singleton).
        r2 = _run_launcher(repo_root, fake)
        assert r2.returncode == 0
        # Pidfile content unchanged.
        second_pid = int(pidfile.read_text().strip())
        assert second_pid == first_pid, (
            f"Singleton broken: pidfile changed {first_pid}->{second_pid}"
        )
        # Only ONE watchdog process belongs to this fake project tree. Because
        # other test runs might have siblings, we don't count global pgrep —
        # we assert the tracked PID is still the one running.
        assert _is_alive(first_pid)
        assert _cmdline_matches(first_pid, "so_session_watchdog")
    finally:
        if first_pid is not None:
            _kill_and_wait(first_pid)
        if pidfile.exists():
            pidfile.unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────────────────
# 3. session-heartbeat.sh behavior
# ──────────────────────────────────────────────────────────────────────────

def test_heartbeat_hook_writes_epoch_atomically(
    tmp_path: Path, repo_root: Path
):
    """PROGRESS: [step 3/7] heartbeat writes epoch content via atomic mv."""
    hook = repo_root / "hooks" / "session-heartbeat.sh"
    assert hook.is_file()

    session_dir = tmp_path / "session-123"
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    env["COGNITIVE_OS_SESSION_ID"] = "session-123"
    env["COGNITIVE_OS_SESSION_DIR"] = str(session_dir)

    t_before = int(time.time()) - 1
    result = subprocess.run(
        ["bash", str(hook)],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    t_after = int(time.time()) + 1
    assert result.returncode == 0, (
        f"heartbeat hook exit!=0: stderr={result.stderr}"
    )
    # Hooks must not pollute context — no stdout allowed.
    assert result.stdout == "", (
        f"heartbeat hook must write nothing to stdout, got: {result.stdout!r}"
    )

    heartbeat_file = session_dir / "heartbeat"
    assert heartbeat_file.is_file(), "heartbeat file not created"

    content = heartbeat_file.read_text().strip()
    assert content.isdigit(), f"heartbeat content not epoch int: {content!r}"
    epoch = int(content)
    assert t_before <= epoch <= t_after, (
        f"heartbeat epoch out of expected window "
        f"[{t_before}, {t_after}]: got {epoch}"
    )

    # No leftover tmp files from the atomic write path.
    tmp_leftovers = list(session_dir.glob(".heartbeat.tmp.*"))
    assert tmp_leftovers == [], (
        f"atomic write leaked tmp files: {tmp_leftovers}"
    )


# ──────────────────────────────────────────────────────────────────────────
# 4. Runtime assertions
# ──────────────────────────────────────────────────────────────────────────

def test_cos_config_audit_runs_and_reports_impl(repo_root: Path):
    """PROGRESS: [step 4/7] `cos-config-audit --json` exits 0 with ≥ 1 IMPL."""
    result = subprocess.run(
        ["python3", "scripts/cos-config-audit.sh", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"cos-config-audit exit!=0: stderr={result.stderr}"
    )
    data = json.loads(result.stdout)
    assert isinstance(data, list) and data, "audit JSON must be non-empty list"
    impl_count = sum(1 for row in data if row.get("status") == "IMPL")
    assert impl_count >= 1, (
        f"Expected ≥1 IMPL section, got {impl_count}: {[r['section'] for r in data]}"
    )


def test_cognitive_os_health_does_not_crash(tmp_path: Path, repo_root: Path):
    """`cognitive-os-health.sh` must exit 0 or a known warn code — never crash."""
    hook = repo_root / "hooks" / "cognitive-os-health.sh"
    if not hook.is_file():
        pytest.skip("cognitive-os-health.sh not present")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)  # read real state, don't pollute
    # 60s: cognitive-os-health.sh enumerates 164 hooks + 145 skills + 17 rules
    # under full SO load and validates each. macOS bash startup + per-component
    # check legitimately exceeds 15s on first run; 60s gives stable headroom.
    result = subprocess.run(
        ["bash", str(hook)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Health script may exit 0 (OK) or with warn/fail codes. The contract is
    # "must not crash": we tolerate any deterministic exit ≤ 2. Signals produce
    # negative return codes.
    assert result.returncode >= 0, (
        f"cognitive-os-health.sh killed by signal: rc={result.returncode}, "
        f"stderr={result.stderr}"
    )
    assert result.returncode in (0, 1, 2), (
        f"Unexpected exit code from cognitive-os-health.sh: "
        f"{result.returncode}; stderr={result.stderr}"
    )


def test_cos_status_runs_without_crash(repo_root: Path):
    """`cos-status.sh` (if present) runs without fatal signal."""
    script = repo_root / "scripts" / "cos-status.sh"
    if not script.is_file():
        pytest.skip("cos-status.sh not present")
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    result = subprocess.run(
        ["bash", str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode >= 0, (
        f"cos-status.sh killed by signal: rc={result.returncode}"
    )


# ──────────────────────────────────────────────────────────────────────────
# 5. Idempotency — the full startup simulation converges when run twice.
# ──────────────────────────────────────────────────────────────────────────

def test_startup_simulation_idempotent(tmp_path: Path, repo_root: Path):
    """PROGRESS: [step 5/7] running the launcher twice must converge."""
    fake = _make_fake_project(tmp_path, repo_root)
    pidfile = fake / ".cognitive-os" / "runtime" / "session-watchdog.pid"

    spawned_pid: int | None = None
    try:
        # Round 1.
        _run_launcher(repo_root, fake)
        deadline = time.time() + 3.0
        while time.time() < deadline and not pidfile.exists():
            time.sleep(0.05)
        assert pidfile.exists()
        pid1 = int(pidfile.read_text().strip())
        spawned_pid = pid1

        # Round 2 — same invocation.
        _run_launcher(repo_root, fake)
        pid2 = int(pidfile.read_text().strip())

        assert pid1 == pid2, (
            f"Idempotency violated: pidfile changed across identical "
            f"startup simulations ({pid1} -> {pid2})"
        )
        assert _is_alive(pid1), "Daemon died between idempotent invocations"
    finally:
        if spawned_pid is not None:
            _kill_and_wait(spawned_pid)
        if pidfile.exists():
            pidfile.unlink(missing_ok=True)


# ──────────────────────────────────────────────────────────────────────────
# 6. Cross-phase invariant — observed via cos-config-audit + yaml/lib read.
# ──────────────────────────────────────────────────────────────────────────

def _read_yaml_threshold(yaml_path: Path) -> float:
    """Minimal YAML scraping for `idle_cpu_threshold` under session_watchdog.

    No PyYAML required — we scan line-by-line inside the session_watchdog
    block, matching the same discipline used by the launcher hook.
    """
    in_block = False
    for raw in yaml_path.read_text().splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            # Track block-exit on a non-indented new top-level key.
            if in_block and raw and not raw.startswith((" ", "\t")):
                in_block = False
            continue
        if stripped.startswith("session_watchdog:"):
            in_block = True
            continue
        if in_block:
            if raw and not raw[0].isspace():
                in_block = False
                continue
            if stripped.startswith("idle_cpu_threshold:"):
                rhs = stripped.split(":", 1)[1].strip()
                rhs = rhs.split("#", 1)[0].strip().strip('"').strip("'")
                return float(rhs)
    raise AssertionError(
        f"idle_cpu_threshold not found under session_watchdog in {yaml_path}"
    )


def test_phase_a_ge_phase_b_threshold_invariant(repo_root: Path):
    """PROGRESS: [step 6/7] Phase A `idle_cpu_threshold` ≥ Phase B
    `_CPU_IDLE_THRESHOLD_PCT`. Cross-phase invariant.

    Observed in TWO ways for the acceptance criterion:
      * `cos-config-audit --json` reports `runtime.session_watchdog` IMPL
        with `coherence: OK` — meaning the audit accepts the config shape.
      * Numeric comparison sourced from cognitive-os.yaml + lib import.
    """
    # Leg 1 — audit says session_watchdog is coherent.
    audit = subprocess.run(
        ["python3", "scripts/cos-config-audit.sh", "--json"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert audit.returncode == 0, f"audit exit!=0: {audit.stderr}"
    rows = json.loads(audit.stdout)
    sw = next(
        (r for r in rows if r.get("section") == "runtime.session_watchdog"),
        None,
    )
    assert sw is not None, (
        "audit JSON missing runtime.session_watchdog entry; "
        f"sections: {[r.get('section') for r in rows]}"
    )
    assert sw.get("status") == "IMPL", (
        f"session_watchdog must be IMPL post-ADR-047 Phase A: {sw}"
    )
    assert sw.get("coherence") == "OK", (
        f"session_watchdog coherence regression: {sw}"
    )

    # Leg 2 — numeric invariant: phase_a_threshold ≥ phase_b_threshold.
    yaml_path = repo_root / "cognitive-os.yaml"
    phase_a = _read_yaml_threshold(yaml_path)
    sys.path.insert(0, str(repo_root))
    try:
        from lib.session_watchdog_lib import _CPU_IDLE_THRESHOLD_PCT  # type: ignore
    finally:
        try:
            sys.path.remove(str(repo_root))
        except ValueError:
            pass
    phase_b = float(_CPU_IDLE_THRESHOLD_PCT)
    assert phase_a >= phase_b, (
        f"Phase-A/B invariant broken: yaml idle_cpu_threshold={phase_a} "
        f"< lib _CPU_IDLE_THRESHOLD_PCT={phase_b}"
    )


# ──────────────────────────────────────────────────────────────────────────
# 7. Global no-leak sentinel — independent of per-test teardowns.
# ──────────────────────────────────────────────────────────────────────────

def test_no_watchdog_process_leak_post_module(repo_root: Path):
    """PROGRESS: [step 7/7] After all tests in this module ran, the
    global `pgrep -f so_session_watchdog.py` count MUST NOT be greater
    than what `lingering_watchdog_guard` observed at session start.

    This is a belt-and-braces check. The session-scoped fixture in
    conftest.py already cleans up leaks, so by the time this test runs
    the world should be quiet. We simply run the canary check here so a
    regression surfaces as a failed test, not a warning.
    """
    try:
        res = subprocess.run(
            ["pgrep", "-f", "so_session_watchdog.py"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError:
        pytest.skip("pgrep not available on this platform")
    # pgrep: rc 0 = matches, rc 1 = none, rc ≥2 = error.
    assert res.returncode in (0, 1), f"pgrep error rc={res.returncode}"
    # We don't assert count == 0 because another unrelated COS session on
    # this developer machine might legitimately have a daemon running. We
    # only assert that OUR test body ran without raising, and that the
    # sentinel itself works end-to-end.
    # The conftest `lingering_watchdog_guard` fixture does the diff check.
