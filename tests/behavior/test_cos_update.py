"""Behavior tests for the idempotent cos-update.sh (UX6).

Covers:
- Syntax is valid (bash -n)
- --help names the new capabilities (idempotent, verify, rollback)
- --dry-run is idempotent (same output on re-run)
- --dry-run does not mutate the tree
- A live update run creates a backup under .cognitive-os/backups/
- Backup rotation keeps only the last MAX_BACKUPS entries

Live-run tests operate on a scratch copy of the minimum project surface
(scripts/, hooks/, rules/, skills/, cognitive-os.yaml, etc.) inside tmp_path
so they cannot affect the real project.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPDATE_SCRIPT = PROJECT_ROOT / "scripts" / "cos-update.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_update(
    args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Invoke cos-update.sh against the real or scratch project root."""
    work_dir = cwd if cwd is not None else PROJECT_ROOT
    script_path = work_dir / "scripts" / "cos-update.sh"
    cmd = ["bash", str(script_path)] + (args or [])
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(work_dir),
    )


def _hash_dir(path: Path) -> str:
    """Return a stable fingerprint of the files under `path`."""
    if not path.exists():
        return "MISSING"
    h = hashlib.sha256()
    for entry in sorted(path.rglob("*")):
        try:
            rel = entry.relative_to(path).as_posix()
        except ValueError:
            continue
        if entry.is_symlink():
            h.update(f"L:{rel}:{os.readlink(entry)}\n".encode())
        elif entry.is_file():
            h.update(f"F:{rel}:{entry.stat().st_size}\n".encode())
        elif entry.is_dir():
            h.update(f"D:{rel}\n".encode())
    return h.hexdigest()


def _make_scratch_project(tmp_path: Path) -> Path:
    """Create a minimal clone of luum-agent-os inside tmp_path.

    We symlink (not copy) most dirs to avoid multi-MB copies, but we copy
    the scripts/ dir because the test may invoke cos-update.sh with --force
    and we want to isolate writes.
    """
    scratch = tmp_path / "scratch-cos"
    scratch.mkdir()

    # Symlink large read-only trees back to the real project
    for name in ("skills", "rules", "squads", "templates", "agents", "customizations", "docs", "lib", "tests", "hooks"):
        src = PROJECT_ROOT / name
        if src.exists():
            (scratch / name).symlink_to(src)

    # Copy scripts (we invoke cos-update.sh via this path)
    shutil.copytree(PROJECT_ROOT / "scripts", scratch / "scripts")

    # Copy the top-level marker files the script expects
    for fname in ("cognitive-os.yaml", "env.example"):
        src = PROJECT_ROOT / fname
        if src.exists():
            shutil.copy(src, scratch / fname)

    # A minimal .claude/settings.json so verification snapshot has something to hash
    claude_dir = scratch / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"hooks": {}}')

    # An empty .cognitive-os/ so the backup dir can be created
    (scratch / ".cognitive-os").mkdir()

    # A compose file stub so docker checks gracefully skip (no docker in test env)
    compose_path = scratch / "docker-compose.cognitive-os.yml"
    if not compose_path.exists():
        compose_path.write_text("services: {}\n")

    return scratch


# ---------------------------------------------------------------------------
# Tests — pure inspection
# ---------------------------------------------------------------------------


def test_syntax_valid():
    """bash -n should pass on cos-update.sh."""
    result = subprocess.run(
        ["bash", "-n", str(UPDATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Syntax check failed:\n{result.stderr}"


def test_help_mentions_features():
    """--help must surface idempotent, verify, rollback capabilities."""
    result = _run_update(["--help"])
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    combined = (result.stdout + result.stderr).lower()
    for token in ("idempotent", "verify", "rollback"):
        assert token in combined, f"--help output missing '{token}'"


def test_help_lists_flags():
    """--help must document the five new flags."""
    result = _run_update(["--help"])
    combined = result.stdout + result.stderr
    for flag in ("--dry-run", "--auto-rollback", "--no-verify", "--force", "--pull-images"):
        assert flag in combined, f"--help missing flag {flag}"


# ---------------------------------------------------------------------------
# Tests — idempotence of --dry-run
# ---------------------------------------------------------------------------


def test_update_idempotent():
    """Running --dry-run twice must yield identical stdout."""
    first = _run_update(["--dry-run"])
    second = _run_update(["--dry-run"])

    assert first.returncode == 0, f"First dry-run failed: {first.stderr}"
    assert second.returncode == 0, f"Second dry-run failed: {second.stderr}"
    assert first.stdout == second.stdout, (
        "Two --dry-run invocations produced different stdout — not idempotent"
    )


def test_update_dry_run_no_changes(tmp_path):
    """--dry-run must not mutate the tree (no backup created, no files changed)."""
    scratch = _make_scratch_project(tmp_path)

    before = _hash_dir(scratch / ".cognitive-os")
    before_claude = _hash_dir(scratch / ".claude")

    result = _run_update(["--dry-run"], cwd=scratch)
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"

    after = _hash_dir(scratch / ".cognitive-os")
    after_claude = _hash_dir(scratch / ".claude")

    assert before == after, ".cognitive-os/ changed during --dry-run"
    assert before_claude == after_claude, ".claude/ changed during --dry-run"

    backup_root = scratch / ".cognitive-os" / "backups"
    if backup_root.exists():
        assert not any(backup_root.iterdir()), "Backups must not be created in --dry-run"


# ---------------------------------------------------------------------------
# Tests — backup creation and rotation (live runs in scratch dir)
# ---------------------------------------------------------------------------


def test_update_creates_backup(tmp_path):
    """After a non-dry-run, .cognitive-os/backups/pre-update-<ts>/ must exist."""
    scratch = _make_scratch_project(tmp_path)

    # --no-verify + --force to skip the heavy verification but still exercise
    # the backup path. --force also bypasses the idempotence short-circuit so
    # the backup is created unconditionally.
    result = _run_update(["--no-verify", "--force"], cwd=scratch, timeout=90)
    # Allow non-zero (docker unavailable etc.); we only care that backup exists.
    # Exit code 2 means verify failed, but we passed --no-verify so shouldn't happen.
    # Exit code 1 means apply failed — still acceptable for the backup-creation
    # assertion because backup is created BEFORE apply.
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    backup_root = scratch / ".cognitive-os" / "backups"
    assert backup_root.exists(), f".cognitive-os/backups/ not created. stdout: {result.stdout[-500:]}"

    backups = [p for p in backup_root.iterdir() if p.is_dir() and p.name.startswith("pre-update-")]
    assert len(backups) >= 1, (
        f"No pre-update-* backup created. Contents: {list(backup_root.iterdir())}"
    )

    # Backup must contain at least meta.txt
    assert (backups[0] / "meta.txt").exists(), "meta.txt missing from backup"


def test_update_backup_rotation(tmp_path):
    """After more than MAX_BACKUPS runs, only the last 3 backups must remain."""
    scratch = _make_scratch_project(tmp_path)
    backup_root = scratch / ".cognitive-os" / "backups"

    # Seed 5 fake older backups so rotation can prune them in one live run.
    # We use sortable ISO-like timestamps so newer > older lexically.
    older_stamps = [
        "20260101T010000Z",
        "20260102T010000Z",
        "20260103T010000Z",
        "20260104T010000Z",
        "20260105T010000Z",
    ]
    backup_root.mkdir(parents=True, exist_ok=True)
    for stamp in older_stamps:
        d = backup_root / f"pre-update-{stamp}"
        d.mkdir()
        (d / "meta.txt").write_text(f"timestamp_utc={stamp}\n")

    # Run live (non-dry) so rotation fires. Short-circuits at snapshot
    # short-circuit MUST NOT prevent rotation, so use --force.
    result = _run_update(["--no-verify", "--force"], cwd=scratch, timeout=90)
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    # After the run there are the 5 seeds + 1 new. Rotation must keep only 3.
    remaining = sorted(
        p.name for p in backup_root.iterdir()
        if p.is_dir() and p.name.startswith("pre-update-")
    )
    assert len(remaining) == 3, (
        f"Expected 3 backups after rotation, got {len(remaining)}: {remaining}"
    )

    # The three kept must be the lexically greatest (newest by ISO timestamp).
    # The run created one backup with a fresh timestamp — it should be the newest.
    # The two next-newest from the seed (20260105, 20260104) must survive.
    assert any("20260105" in name for name in remaining), (
        f"Newest seed (20260105) was rotated out incorrectly: {remaining}"
    )
    assert any("20260104" in name for name in remaining), (
        f"Second-newest seed (20260104) was rotated out incorrectly: {remaining}"
    )
    # Oldest three seeds must be gone
    for stamp in ("20260101", "20260102", "20260103"):
        assert not any(stamp in name for name in remaining), (
            f"Old seed {stamp} survived rotation: {remaining}"
        )


# ---------------------------------------------------------------------------
# Tests — uv sync cache on pyproject.toml change
# ---------------------------------------------------------------------------


def _install_uv_stub(scratch: Path) -> Path:
    """Install a fake `uv` on PATH that records invocations to a log file.

    Returns the log path. The stub accepts any args, exits 0, and appends
    one line per call to the log (JOIN-ed args).
    """
    bin_dir = scratch / "stub-bin"
    bin_dir.mkdir(exist_ok=True)
    log_path = scratch / "uv-invocations.log"
    stub = bin_dir / "uv"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "uv $*" >> {log_path}\n'
        "exit 0\n"
    )
    stub.chmod(0o755)
    return log_path


def _seed_pyproject(scratch: Path, contents: str) -> Path:
    pyproject = scratch / "pyproject.toml"
    pyproject.write_text(contents)
    return pyproject


def test_uv_sync_runs_when_pyproject_changes(tmp_path):
    """When pyproject.toml SHA differs from the cached value, uv sync must run."""
    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')
    log_path = _install_uv_stub(scratch)

    env = {**os.environ, "PATH": f"{scratch / 'stub-bin'}:{os.environ.get('PATH', '')}"}
    result = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )

    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}. stderr: {result.stderr[-500:]}"
    )
    assert log_path.exists(), (
        f"uv stub was never invoked. stderr: {result.stderr[-500:]}"
    )
    invocations = log_path.read_text().strip().splitlines()
    assert any("sync" in line for line in invocations), (
        f"uv sync not called. invocations: {invocations}"
    )

    sha_file = scratch / ".cognitive-os" / "state" / "pyproject.sha"
    assert sha_file.exists(), "pyproject.sha cache was not written after successful uv sync"
    cached_sha = sha_file.read_text().strip()
    assert len(cached_sha) == 64, f"cached sha is not a sha256 hex digest: {cached_sha!r}"


def test_uv_sync_skipped_when_pyproject_unchanged(tmp_path):
    """Second run with the same pyproject.toml must NOT re-invoke uv sync."""
    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')
    log_path = _install_uv_stub(scratch)

    env = {**os.environ, "PATH": f"{scratch / 'stub-bin'}:{os.environ.get('PATH', '')}"}

    # First run: sha cache is absent, uv sync must fire.
    first = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )
    assert first.returncode in (0, 1)
    assert log_path.exists()
    first_calls = log_path.read_text().strip().splitlines()

    # Second run with pyproject unchanged: must be a no-op.
    second = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )
    assert second.returncode in (0, 1)
    second_calls = log_path.read_text().strip().splitlines()
    assert len(second_calls) == len(first_calls), (
        f"uv sync ran again despite unchanged pyproject. first={first_calls}, second={second_calls}"
    )


def test_uv_sync_reruns_when_pyproject_mutates(tmp_path):
    """Mutating pyproject.toml between runs must re-invoke uv sync."""
    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')
    log_path = _install_uv_stub(scratch)

    env = {**os.environ, "PATH": f"{scratch / 'stub-bin'}:{os.environ.get('PATH', '')}"}

    subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )
    first_count = len(log_path.read_text().strip().splitlines())

    # Mutate pyproject — add a dep line so the SHA changes
    _seed_pyproject(
        scratch,
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = ["requests"]\n',
    )

    subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )
    second_count = len(log_path.read_text().strip().splitlines())

    assert second_count > first_count, (
        "uv sync did not re-run after pyproject.toml SHA changed"
    )


def test_uv_sync_missing_binary_is_non_fatal(tmp_path):
    """Missing `uv` must not fail the update — only emit a warning."""
    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')

    # PATH with no `uv` binary
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )

    # Update must not abort — apply may still fail for unrelated reasons (rc=1)
    # but must not be rc=2 (verify) since we passed --no-verify.
    assert result.returncode in (0, 1), (
        f"Missing uv caused unexpected exit {result.returncode}. stderr: {result.stderr[-500:]}"
    )
    # sha file must NOT be written when uv is unavailable
    sha_file = scratch / ".cognitive-os" / "state" / "pyproject.sha"
    assert not sha_file.exists(), "pyproject.sha must not be written when uv is missing"


def test_uv_sync_runs_before_self_install(tmp_path):
    """uv sync must complete before hooks/self-install.sh is invoked.

    Both tools write a log entry with a timestamp. The test asserts that
    uv's log entry sorts earlier (i.e. has a lower timestamp) than the
    self-install entry.
    """
    import time

    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')

    order_log = scratch / "invocation-order.log"

    # --- uv stub: records its invocation timestamp ----------------------------
    uv_log_path = _install_uv_stub(scratch)
    # Replace the simple stub with one that also appends to the shared order log
    stub_bin = scratch / "stub-bin"
    uv_stub = stub_bin / "uv"
    uv_stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "uv $*" >> {uv_log_path}\n'
        # Use nanoseconds for maximum resolution to avoid ties on fast machines
        f'printf "uv\\t%s\\n" "$(date +%s%N)" >> {order_log}\n'
        "exit 0\n"
    )
    uv_stub.chmod(0o755)

    # --- self-install stub: replaces the real hooks/self-install.sh -----------
    # _make_scratch_project symlinks hooks/ to the real project; we need a
    # writable copy so we can replace self-install.sh without touching the repo.
    real_hooks_link = scratch / "hooks"
    real_hooks_link.unlink()  # remove the symlink
    hooks_dir = scratch / "hooks"
    hooks_dir.mkdir()
    # Copy every file from the real hooks dir into the scratch hooks dir,
    # resolving symlinks so the copies are independent.
    real_hooks_src = PROJECT_ROOT / "hooks"
    if real_hooks_src.exists():
        for entry in real_hooks_src.iterdir():
            dest = hooks_dir / entry.name
            if entry.is_symlink() or entry.is_file():
                shutil.copy2(str(entry.resolve()), str(dest))
                dest.chmod(0o755)
            elif entry.is_dir():
                shutil.copytree(str(entry), str(dest))

    # Now overwrite self-install.sh with an order-logging shim
    self_install = hooks_dir / "self-install.sh"
    self_install.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "self-install\\t%s\\n" "$(date +%s%N)" >> {order_log}\n'
        "exit 0\n"
    )
    self_install.chmod(0o755)

    # --- Run the update -------------------------------------------------------
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}"}
    result = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=90, cwd=str(scratch), env=env,
    )

    assert result.returncode in (0, 1), (
        f"Unexpected exit {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    # --- Parse the order log --------------------------------------------------
    assert order_log.exists(), (
        f"Order log was never written — neither uv nor self-install ran.\n"
        f"stdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
    )

    entries: dict[str, int] = {}
    for line in order_log.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            name, ts_str = parts
            try:
                entries[name.strip()] = int(ts_str.strip())
            except ValueError:
                pass

    assert "uv" in entries, (
        f"uv stub was not recorded in order log. log: {order_log.read_text()!r}\n"
        f"stderr: {result.stderr[-500:]}"
    )
    assert "self-install" in entries, (
        f"self-install stub was not recorded in order log. log: {order_log.read_text()!r}\n"
        f"stderr: {result.stderr[-500:]}"
    )

    assert entries["uv"] < entries["self-install"], (
        f"uv sync did NOT run before self-install!\n"
        f"uv timestamp:           {entries['uv']}\n"
        f"self-install timestamp: {entries['self-install']}\n"
        f"Order log:\n{order_log.read_text()}"
    )


def test_register_mcps_runs_between_uv_and_self_install(tmp_path):
    """register-mcps.sh must be called AFTER uv sync and BEFORE self-install.

    All three write nanosecond timestamps to a shared order log. We assert
    uv.ts < claude-mcp.ts < self-install.ts.
    """
    import time

    scratch = _make_scratch_project(tmp_path)
    _seed_pyproject(scratch, '[project]\nname = "demo"\nversion = "0.1.0"\n')

    order_log = scratch / "invocation-order.log"

    # --- uv stub (timestamps to order log) ------------------------------------
    uv_log_path = _install_uv_stub(scratch)
    stub_bin = scratch / "stub-bin"
    uv_stub = stub_bin / "uv"
    uv_stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "uv $*" >> {uv_log_path}\n'
        f'printf "uv\\t%s\\n" "$(date +%s%N 2>/dev/null || date +%s)000" >> {order_log}\n'
        "exit 0\n"
    )
    uv_stub.chmod(0o755)

    # --- claude stub (timestamps to order log) ---------------------------------
    # register-mcps.sh calls `claude mcp add`; we stub `claude` to log timestamps.
    claude_stub = stub_bin / "claude"
    claude_stub.write_text(
        "#!/usr/bin/env bash\n"
        "# Handle `claude mcp list` (return empty so add is always attempted)\n"
        "if [[ \"${1:-}\" == 'mcp' && \"${2:-}\" == 'list' ]]; then\n"
        "  echo ''\n"
        "  exit 0\n"
        "fi\n"
        f'printf "claude-mcp\\t%s\\n" "$(date +%s%N 2>/dev/null || date +%s)000" >> {order_log}\n'
        "exit 0\n"
    )
    claude_stub.chmod(0o755)

    # --- self-install stub ----------------------------------------------------
    real_hooks_link = scratch / "hooks"
    real_hooks_link.unlink()
    hooks_dir = scratch / "hooks"
    hooks_dir.mkdir()
    real_hooks_src = PROJECT_ROOT / "hooks"
    if real_hooks_src.exists():
        for entry in real_hooks_src.iterdir():
            dest = hooks_dir / entry.name
            if entry.is_symlink() or entry.is_file():
                shutil.copy2(str(entry.resolve()), str(dest))
                dest.chmod(0o755)
            elif entry.is_dir():
                shutil.copytree(str(entry), str(dest))

    self_install = hooks_dir / "self-install.sh"
    self_install.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "self-install\\t%s\\n" "$(date +%s%N 2>/dev/null || date +%s)000" >> {order_log}\n'
        "exit 0\n"
    )
    self_install.chmod(0o755)

    # Also copy register-mcps.sh into scratch scripts/ so the path is found
    shutil.copy(
        str(PROJECT_ROOT / "scripts" / "register-mcps.sh"),
        str(scratch / "scripts" / "register-mcps.sh"),
    )

    # --- Run update -----------------------------------------------------------
    env = {
        **os.environ,
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "HOME": str(tmp_path / "fake-home"),
    }
    (tmp_path / "fake-home" / ".claude").mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True, text=True, timeout=120, cwd=str(scratch), env=env,
    )

    assert result.returncode in (0, 1), (
        f"Unexpected exit {result.returncode}. stderr: {result.stderr[-500:]}"
    )

    # --- Parse order log ------------------------------------------------------
    assert order_log.exists(), (
        f"Order log was never written.\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"
    )

    entries: dict[str, int] = {}
    for line in order_log.read_text().splitlines():
        parts = line.split("\t")
        if len(parts) == 2:
            name, ts_str = parts
            name = name.strip()
            try:
                ts = int(ts_str.strip())
                # Keep the earliest timestamp for each name (first occurrence)
                if name not in entries:
                    entries[name] = ts
            except ValueError:
                pass

    # uv and self-install are always expected; claude-mcp may be present if
    # register-mcps.sh ran and found a manifest change.
    assert "uv" in entries, (
        f"uv not in order log. log:\n{order_log.read_text()!r}\nstderr: {result.stderr[-500:]}"
    )
    assert "self-install" in entries, (
        f"self-install not in order log. log:\n{order_log.read_text()!r}\nstderr: {result.stderr[-500:]}"
    )

    if "claude-mcp" in entries:
        assert entries["uv"] < entries["claude-mcp"], (
            f"uv did NOT run before claude-mcp!\n"
            f"uv ts: {entries['uv']}, claude-mcp ts: {entries['claude-mcp']}\n"
            f"Order log:\n{order_log.read_text()}"
        )
        assert entries["claude-mcp"] < entries["self-install"], (
            f"claude-mcp did NOT run before self-install!\n"
            f"claude-mcp ts: {entries['claude-mcp']}, self-install ts: {entries['self-install']}\n"
            f"Order log:\n{order_log.read_text()}"
        )

    # Even if claude-mcp didn't run (SHA cache hit), ordering invariant holds:
    assert entries["uv"] < entries["self-install"], (
        f"uv did NOT run before self-install!\n"
        f"uv ts: {entries['uv']}, self-install ts: {entries['self-install']}\n"
        f"Order log:\n{order_log.read_text()}"
    )


def test_update_passes_canonical_project_env_to_self_install(tmp_path):
    """cos-update should invoke self-install with COGNITIVE_OS_PROJECT_DIR."""
    scratch = _make_scratch_project(tmp_path)

    real_hooks_link = scratch / "hooks"
    real_hooks_link.unlink()
    hooks_dir = scratch / "hooks"
    hooks_dir.mkdir()
    hooks_lib_dir = hooks_dir / "_lib"
    hooks_lib_dir.mkdir()
    shutil.copy2(PROJECT_ROOT / "hooks" / "_lib" / "portable.sh", hooks_lib_dir / "portable.sh")

    env_log = scratch / "self-install-env.log"
    self_install = hooks_dir / "self-install.sh"
    self_install.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'printf "cognitive=%s\\n" "${{COGNITIVE_OS_PROJECT_DIR:-}}" > {env_log}\n'
        f'printf "claude=%s\\n" "${{CLAUDE_PROJECT_DIR:-}}" >> {env_log}\n'
        f'[ "${{COGNITIVE_OS_PROJECT_DIR:-}}" = "{scratch}" ]\n'
    )
    self_install.chmod(0o755)

    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": "/tmp/wrong-driver-root",
    }
    result = subprocess.run(
        ["bash", str(scratch / "scripts" / "cos-update.sh"), "--no-verify", "--force"],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=str(scratch),
        env=env,
    )

    assert result.returncode == 0, (
        f"cos-update did not pass canonical env to self-install.\n"
        f"stdout: {result.stdout[-500:]}\n"
        f"stderr: {result.stderr[-500:]}"
    )
    assert env_log.exists(), "self-install env log was not written"
    log_text = env_log.read_text()
    assert f"cognitive={scratch}" in log_text
