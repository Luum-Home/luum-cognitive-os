"""Behavior tests for scripts/register-mcps.sh and lib/manifest_loader.get_mcps_for_profile.

Covers:
- Bash syntax validity
- --help documents all flags
- --dry-run does not mutate files
- Registration via claude CLI stub
- SHA cache skips re-registration on second identical run
- Fallback to settings.json when claude is absent
- Re-registration when manifest changes

All tests use a scratch HOME and scratch state dir to avoid touching the real
~/.claude/settings.json or cached state.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTER_SCRIPT = PROJECT_ROOT / "scripts" / "register-mcps.sh"
MANIFEST_PATH = PROJECT_ROOT / "manifests" / "dependencies.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_script(
    args: list[str],
    env: dict | None = None,
    home: Path | None = None,
    cache_dir: Path | None = None,
    manifest_path: Path | None = None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run register-mcps.sh with the given args and optional env overrides."""
    full_env = {**os.environ}
    if env:
        full_env.update(env)
    if home:
        full_env["HOME"] = str(home)
    if manifest_path:
        full_env["COS_MANIFEST_PATH"] = str(manifest_path)

    cmd = ["bash", str(REGISTER_SCRIPT)] + args
    if cache_dir:
        # Insert --cache-dir before any trailing args
        cmd = ["bash", str(REGISTER_SCRIPT), "--cache-dir", str(cache_dir)] + args

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=full_env,
        cwd=str(PROJECT_ROOT),
    )


def _make_claude_stub(bin_dir: Path, log_path: Path) -> None:
    """Install a fake `claude` binary that logs invocations and exits 0.

    ``claude mcp list`` always returns empty so registration is always
    attempted (tests that need idempotent-skip behaviour should use
    ``_make_stateful_claude_stub`` instead).
    """
    stub = bin_dir / "claude"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "claude $*" >> {log_path}\n'
        "# Simulate `claude mcp list` returning empty (so we always attempt add)\n"
        "if [[ \"$1\" == 'mcp' && \"$2\" == 'list' ]]; then\n"
        "  echo ''\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n"
    )
    stub.chmod(0o755)


def _make_stateful_claude_stub(bin_dir: Path, log_path: Path, registered_file: Path) -> None:
    """Install a fake `claude` binary that maintains a registered-MCPs state file.

    - ``claude mcp add <name> ...`` appends <name> to *registered_file* and logs the call.
    - ``claude mcp list`` outputs the current contents of *registered_file* (one name per line).
    - ``claude mcp remove <name>`` removes the matching line from *registered_file*.

    This lets tests simulate user-removal (drift) by directly editing *registered_file*
    between runs, while the stub faithfully reflects actual registered state on ``mcp list``.
    """
    stub = bin_dir / "claude"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'REGISTERED_FILE="{registered_file}"\n'
        f'LOG_FILE="{log_path}"\n'
        'echo "claude $*" >> "$LOG_FILE"\n'
        "\n"
        'if [[ "$1" == "mcp" && "$2" == "list" ]]; then\n'
        '  if [[ -f "$REGISTERED_FILE" ]]; then\n'
        '    cat "$REGISTERED_FILE"\n'
        '  fi\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        'if [[ "$1" == "mcp" && "$2" == "add" ]]; then\n'
        '  name="$3"\n'
        '  touch "$REGISTERED_FILE"\n'
        '  # Only append if not already present\n'
        '  if ! grep -qxF "$name" "$REGISTERED_FILE" 2>/dev/null; then\n'
        '    echo "$name" >> "$REGISTERED_FILE"\n'
        '  fi\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        'if [[ "$1" == "mcp" && "$2" == "remove" ]]; then\n'
        '  name="$3"\n'
        '  if [[ -f "$REGISTERED_FILE" ]]; then\n'
        '    grep -vxF "$name" "$REGISTERED_FILE" > "$REGISTERED_FILE.tmp" 2>/dev/null || true\n'
        '    mv "$REGISTERED_FILE.tmp" "$REGISTERED_FILE"\n'
        '  fi\n'
        "  exit 0\n"
        "fi\n"
        "\n"
        "exit 0\n"
    )
    stub.chmod(0o755)


def _make_scratch_manifest(scratch: Path, extra_mcp: dict | None = None) -> Path:
    """Copy the real manifest to scratch, optionally appending an extra MCP."""
    target = scratch / "dependencies.yaml"
    shutil.copy(MANIFEST_PATH, target)

    if extra_mcp:
        # Append a new MCP entry (raw YAML append — simple and bash 3.2 safe)
        with open(target, "a") as f:
            f.write(f"\n  - name: {extra_mcp['name']}\n")
            f.write(f"    criticality: optional\n")
            f.write(f"    transport: stdio\n")
            f.write(f"    command: {extra_mcp['command']}\n")
            f.write(f"    args: []\n")
            f.write(f"    register_to: ~/.claude/settings.json\n")

    return target


# ---------------------------------------------------------------------------
# Pure inspection tests
# ---------------------------------------------------------------------------


def test_script_syntax_valid():
    """bash -n must exit 0."""
    result = subprocess.run(
        ["bash", "-n", str(REGISTER_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Syntax check failed:\n{result.stderr}"


def test_help_documents_flags():
    """--help must list --profile, --dry-run, and --cache-dir."""
    result = subprocess.run(
        ["bash", str(REGISTER_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"--help failed: {result.stderr}"
    combined = result.stdout + result.stderr
    for flag in ("--profile", "--dry-run", "--cache-dir"):
        assert flag in combined, f"--help missing {flag!r}. output:\n{combined}"


def test_register_mcps_skips_non_claude_driver(tmp_path):
    """Codex-hosted runs must not silently write Claude MCP settings."""
    project = tmp_path / "project"
    project.mkdir()
    (project / ".codex").mkdir()
    (project / ".codex" / "hooks.json").write_text('{"hooks": {}}\n')
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()

    result = _run_script(
        ["--profile", "default"],
        env={
            "COGNITIVE_OS_PROJECT_DIR": str(project),
            "COGNITIVE_OS_HARNESS": "codex",
        },
        home=scratch_home,
    )

    assert result.returncode == 0, result.stderr
    assert "Claude MCP registration only" in result.stderr
    assert "active driver is .codex/hooks.json" in result.stderr
    assert not (scratch_home / ".claude" / "settings.json").exists()


# ---------------------------------------------------------------------------
# --dry-run immutability
# ---------------------------------------------------------------------------


def test_dry_run_no_mutation(tmp_path):
    """--dry-run must not create or modify any files."""
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    scratch_cache = tmp_path / "state"

    # Capture state BEFORE
    def _snapshot(d: Path) -> set[str]:
        if not d.exists():
            return set()
        return {str(p.relative_to(d)) for p in d.rglob("*")}

    home_before = _snapshot(scratch_home)
    cache_before = _snapshot(scratch_cache)

    result = subprocess.run(
        [
            "bash", str(REGISTER_SCRIPT),
            "--profile", "default",
            "--dry-run",
            "--cache-dir", str(scratch_cache),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ, "HOME": str(scratch_home)},
        cwd=str(PROJECT_ROOT),
    )
    # Must succeed (or gracefully degrade)
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"

    home_after = _snapshot(scratch_home)
    cache_after = _snapshot(scratch_cache)

    assert home_before == home_after, (
        f"HOME was mutated during --dry-run. New files: {home_after - home_before}"
    )
    assert cache_before == cache_after, (
        f"Cache dir was mutated during --dry-run. New files: {cache_after - cache_before}"
    )


# ---------------------------------------------------------------------------
# Registration via claude CLI stub
# ---------------------------------------------------------------------------


def test_registers_via_claude_cli_stub(tmp_path):
    """claude mcp add must be invoked once per MCP in the profile."""
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    scratch_cache = tmp_path / "state"
    scratch_cache.mkdir()

    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    log_path = tmp_path / "claude-invocations.log"
    _make_claude_stub(bin_dir, log_path)

    # Count MCPs in 'default' profile
    mcp_count_result = subprocess.run(
        [
            "python3", "-c",
            "import sys; sys.path.insert(0,'lib'); "
            "from manifest_loader import get_mcps_for_profile; "
            "mcps = get_mcps_for_profile('default'); "
            f"print(len(mcps))",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(PROJECT_ROOT),
    )
    expected_count = int(mcp_count_result.stdout.strip()) if mcp_count_result.returncode == 0 else 1

    env = {
        **os.environ,
        "HOME": str(scratch_home),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
    }
    result = subprocess.run(
        [
            "bash", str(REGISTER_SCRIPT),
            "--profile", "default",
            "--cache-dir", str(scratch_cache),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert log_path.exists(), (
        f"claude stub was never invoked. stderr: {result.stderr}"
    )

    invocations = log_path.read_text().strip().splitlines()
    add_calls = [line for line in invocations if "mcp add" in line]
    assert len(add_calls) >= expected_count, (
        f"Expected at least {expected_count} 'mcp add' call(s), got {len(add_calls)}.\n"
        f"Invocations: {invocations}\nstderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Per-MCP idempotence — no re-registration when MCPs are already present
# ---------------------------------------------------------------------------


def test_skipped_when_sha_unchanged(tmp_path):
    """Second run with unchanged manifest must NOT issue new `mcp add` calls.

    The SHA cache is no longer a correctness gate (it was removed to fix the
    declared-vs-actual drift bug — see ADR-025).  Idempotence is now provided
    by the per-MCP check: `claude mcp list` is consulted for each MCP, and
    `add` is skipped when the name is already present.

    This test uses the *stateful* stub so that MCPs registered on the first
    run appear in `mcp list` output on the second run.
    """
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    scratch_cache = tmp_path / "state"
    scratch_cache.mkdir()

    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    log_path = tmp_path / "claude-invocations.log"
    registered_file = tmp_path / "registered-mcps.txt"
    _make_stateful_claude_stub(bin_dir, log_path, registered_file)

    env = {
        **os.environ,
        "HOME": str(scratch_home),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
    }
    common_args = [
        "bash", str(REGISTER_SCRIPT),
        "--profile", "default",
        "--cache-dir", str(scratch_cache),
    ]

    # First run — should register all MCPs
    r1 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r1.returncode == 0, f"First run failed: {r1.stderr}"
    first_log = log_path.read_text() if log_path.exists() else ""
    first_add_count = first_log.count("mcp add")

    # Second run — same manifest, MCPs now in registered_file → should skip adds
    r2 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r2.returncode == 0, f"Second run failed: {r2.stderr}"
    second_log = log_path.read_text() if log_path.exists() else ""
    second_add_count = second_log.count("mcp add")

    assert second_add_count == first_add_count, (
        f"Per-MCP check failed: new 'mcp add' calls issued on second run despite MCPs "
        f"already being registered.\n"
        f"first add count={first_add_count}, second add count={second_add_count}\n"
        f"log after second run:\n{second_log}\nstderr2: {r2.stderr}"
    )


# ---------------------------------------------------------------------------
# Fallback to settings.json when claude is absent
# ---------------------------------------------------------------------------


def test_fallback_to_settings_json_when_no_claude(tmp_path):
    """With empty PATH (no claude), mcpServers must be written to settings.json."""
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    (scratch_home / ".claude").mkdir()
    scratch_cache = tmp_path / "state"
    scratch_cache.mkdir()

    env = {
        **os.environ,
        "HOME": str(scratch_home),
        "PATH": "/usr/bin:/bin",  # no claude
    }
    result = subprocess.run(
        [
            "bash", str(REGISTER_SCRIPT),
            "--profile", "default",
            "--cache-dir", str(scratch_cache),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    settings_path = scratch_home / ".claude" / "settings.json"
    assert settings_path.exists(), (
        f"settings.json not created. stderr: {result.stderr}"
    )
    settings = json.loads(settings_path.read_text())
    assert "mcpServers" in settings, (
        f"mcpServers missing from settings.json. content: {settings}"
    )
    mcp_servers = settings["mcpServers"]
    assert len(mcp_servers) >= 1, (
        f"Expected at least 1 MCP in settings.json. got: {mcp_servers}"
    )


# ---------------------------------------------------------------------------
# Re-registration when manifest changes
# ---------------------------------------------------------------------------


def test_reruns_when_manifest_changes(tmp_path):
    """Modifying the manifest must re-invoke the claude stub on next run."""
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    scratch_cache = tmp_path / "state"
    scratch_cache.mkdir()

    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    log_path = tmp_path / "claude-invocations.log"
    _make_claude_stub(bin_dir, log_path)

    # Use a scratch copy of the manifest
    scratch_manifest = tmp_path / "dependencies.yaml"
    shutil.copy(MANIFEST_PATH, scratch_manifest)

    env = {
        **os.environ,
        "HOME": str(scratch_home),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "COS_MANIFEST_PATH": str(scratch_manifest),
    }
    common_args = [
        "bash", str(REGISTER_SCRIPT),
        "--profile", "default",
        "--cache-dir", str(scratch_cache),
    ]

    # First run
    r1 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r1.returncode == 0, f"First run failed: {r1.stderr}"
    first_count = len(log_path.read_text().strip().splitlines()) if log_path.exists() else 0

    # Mutate the manifest (add a comment at the end so SHA changes)
    with open(scratch_manifest, "a") as f:
        f.write("\n# test mutation\n")

    # Second run — manifest changed, must re-register
    r2 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r2.returncode == 0, f"Second run failed: {r2.stderr}"
    second_count = len(log_path.read_text().strip().splitlines()) if log_path.exists() else 0

    assert second_count > first_count, (
        f"claude stub NOT re-invoked after manifest mutation.\n"
        f"first_count={first_count}, second_count={second_count}\n"
        f"stderr2: {r2.stderr}"
    )


# ---------------------------------------------------------------------------
# Drift regression — re-register when MCP removed despite unchanged manifest
# ---------------------------------------------------------------------------


def test_reregisters_when_mcp_missing_despite_unchanged_manifest(tmp_path):
    """Removing an MCP out-of-band must be caught and repaired on the next run.

    Scenario (the drift bug, fixed in ADR-025):
      1. Manifest declares MCPs A, B, C.  First run installs all.  SHA saved.
      2. User manually removes B (claude mcp remove B / edits settings.json).
      3. git pull with NO manifest change → SHA unchanged.
      4. BEFORE the fix: early-exit fired → B was never reinstalled.
         AFTER the fix:  per-MCP loop runs → B is detected as missing → reinstalled.

    Assertions:
      - B receives a second `mcp add` call on the second run.
      - A and C do NOT receive a second `mcp add` call (still idempotent).
    """
    scratch_home = tmp_path / "home"
    scratch_home.mkdir()
    scratch_cache = tmp_path / "state"
    scratch_cache.mkdir()

    bin_dir = tmp_path / "stub-bin"
    bin_dir.mkdir()
    log_path = tmp_path / "claude-invocations.log"
    registered_file = tmp_path / "registered-mcps.txt"
    _make_stateful_claude_stub(bin_dir, log_path, registered_file)

    # Build a scratch manifest with exactly 3 deterministic MCPs so the test
    # is independent of the real manifest content.
    scratch_manifest = tmp_path / "dependencies.yaml"
    scratch_manifest.write_text(
        textwrap.dedent("""\
        schema_version: 1

        python:
          required: []

        mcp_servers:
          - name: drift-alpha
            criticality: optional
            transport: stdio
            command: /bin/echo
            args: ["alpha"]
            register_to: ~/.claude/settings.json
          - name: drift-beta
            criticality: optional
            transport: stdio
            command: /bin/echo
            args: ["beta"]
            register_to: ~/.claude/settings.json
          - name: drift-gamma
            criticality: optional
            transport: stdio
            command: /bin/echo
            args: ["gamma"]
            register_to: ~/.claude/settings.json

        profiles:
          default:
            python_groups: []
            tools_required: []
            tools_recommended: []
            mcp_servers_recommended:
              - drift-alpha
              - drift-beta
              - drift-gamma
        """)
    )

    env = {
        **os.environ,
        "HOME": str(scratch_home),
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "COS_MANIFEST_PATH": str(scratch_manifest),
    }
    common_args = [
        "bash", str(REGISTER_SCRIPT),
        "--profile", "default",
        "--cache-dir", str(scratch_cache),
    ]

    # --- First run: register all three MCPs ---------------------------------
    r1 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r1.returncode == 0, f"First run failed:\n{r1.stderr}"

    # Verify all three were added
    first_log = log_path.read_text() if log_path.exists() else ""
    for name in ("drift-alpha", "drift-beta", "drift-gamma"):
        assert f"mcp add {name}" in first_log, (
            f"Expected first run to add '{name}'.\nLog:\n{first_log}\nstderr:\n{r1.stderr}"
        )

    # Verify registered_file contains all three
    registered_names = registered_file.read_text().strip().splitlines()
    assert "drift-beta" in registered_names, (
        f"drift-beta missing from registered_file after first run: {registered_names}"
    )

    # --- Simulate user removal of drift-beta --------------------------------
    # Edit registered_file directly (simulates `claude mcp remove drift-beta`)
    remaining = [n for n in registered_names if n != "drift-beta"]
    registered_file.write_text("\n".join(remaining) + ("\n" if remaining else ""))

    # Clear the log so second-run counts are unambiguous
    log_path.write_text("")

    # --- Second run: manifest UNCHANGED (SHA identical) ---------------------
    r2 = subprocess.run(
        common_args, capture_output=True, text=True, timeout=30, env=env, cwd=str(PROJECT_ROOT),
    )
    assert r2.returncode == 0, f"Second run failed:\n{r2.stderr}"

    second_log = log_path.read_text()

    # drift-beta MUST be re-added (drift recovery)
    assert "mcp add drift-beta" in second_log, (
        f"REGRESSION: drift-beta was NOT re-registered on second run despite being "
        f"removed.\nThe SHA-cache early-exit may have been re-introduced.\n"
        f"Second-run log:\n{second_log}\nstderr:\n{r2.stderr}"
    )

    # drift-alpha and drift-gamma must NOT be re-added (still idempotent)
    for name in ("drift-alpha", "drift-gamma"):
        assert f"mcp add {name}" not in second_log, (
            f"'{name}' was unnecessarily re-registered on second run (idempotence broken).\n"
            f"Second-run log:\n{second_log}\nstderr:\n{r2.stderr}"
        )
