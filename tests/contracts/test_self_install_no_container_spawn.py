"""Contract: SessionStart hooks MUST NOT spawn Docker containers.

Catalog doctrine (docs/architecture/infrastructure-service-catalog.md) says
`hooks/self-install.sh` and every hook registered under the `SessionStart`
matcher in `.claude/settings.json` must not implicitly start containers.
Reference stacks are opt-in. Any hook that calls `docker compose up`,
`docker run`, `docker start`, `docker exec`, etc. during SessionStart is a
contract breach unless explicitly justified via
`tests/contracts/docker_spawn_allowlist.txt`.

How this test works:
1. A bash `docker` shim is installed on PATH ahead of the real binary.
2. The shim writes argv of every invocation to `$DOCKER_SHIM_LOG`.
3. Container-spawning subcommands additionally append to `$DOCKER_SPAWN_LOG`.
4. Every SessionStart hook is executed under the shim with `bash -n` first
   (syntax check, cheap) and then with `bash` (real run).
5. Spawns in `$DOCKER_SPAWN_LOG` are matched against the allowlist; any
   unmatched spawn fails the test.

Helpers reused: `tests/unit._helpers.requires_bash` gates the suite when
bash is not installed, and `tests/utils.jsonl` is the JSONL reader of choice
if we later want evidence rolled up from metrics.

Timing: Each hook runs once; full suite is designed to fit comfortably under
30 seconds (hook syntax checks + short runs with a stub binary).
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure the tests package root is importable (for _helpers when invoked from
# different working directories).
_TESTS_ROOT = Path(__file__).resolve().parents[1]
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

from unit._helpers import requires_bash  # noqa: E402

pytestmark = [pytest.mark.contract, pytest.mark.unit, requires_bash]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Commands that spawn (or can spawn) containers. Matched against the first
# and second argv tokens of the docker invocation.
_SPAWN_SUBCOMMANDS_FIRST = {"run", "start", "exec"}
_SPAWN_SUBCOMMANDS_COMPOSE = {"up", "start", "run", "exec"}

# Read-only subcommands — allowed without allowlist entry.
_READONLY_SUBCOMMANDS = {
    "ps", "inspect", "version", "info", "images", "network", "volume",
    "container", "image", "system", "stats", "logs", "port", "top", "diff",
    "events", "history", "wait", "search",
}

# Hooks that are launchers of their own; we don't execute them under the shim
# because they detach child processes that escape the shim and the shim has
# no supervisory control. We still test them for syntax.
_LAUNCHER_HOOKS = {
    "reaper-daemon-launcher.sh",
    "session-watchdog-launcher.sh",
    "cos-executor-daemon-launcher.sh",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_sessionstart_hooks() -> list[Path]:
    settings_path = _repo_root() / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    hooks = []
    for group in settings.get("hooks", {}).get("SessionStart", []):
        for hook in group.get("hooks", []):
            cmd = hook.get("command", "")
            # command is `bash "$CLAUDE_PROJECT_DIR/hooks/NAME.sh"`
            for token in cmd.split():
                token = token.strip('"').strip("'")
                if token.endswith(".sh") and "/hooks/" in token:
                    rel = token.split("/hooks/", 1)[1]
                    hook_path = _repo_root() / "hooks" / rel
                    hooks.append(hook_path)
    return hooks


def _load_allowlist() -> set[str]:
    path = Path(__file__).parent / "docker_spawn_allowlist.txt"
    allowed: set[str] = set()
    if not path.exists():
        return allowed
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # format: <hook_path>: <justification>
        hook_part = line.split(":", 1)[0].strip()
        if hook_part:
            allowed.add(hook_part)
    return allowed


def _install_shim(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Return (bin_dir, invocations_log, spawns_log)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    invocations_log = tmp_path / "docker-invocations.log"
    spawns_log = tmp_path / "docker-spawns.log"
    invocations_log.write_text("", encoding="utf-8")
    spawns_log.write_text("", encoding="utf-8")

    shim = bin_dir / "docker"
    shim.write_text(
        _DOCKER_SHIM_BODY.format(
            invocations_log=invocations_log,
            spawns_log=spawns_log,
        ),
        encoding="utf-8",
    )
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir, invocations_log, spawns_log


# The shim is a posix-sh script. It classifies subcommand as spawn / readonly.
# For `docker compose <sub>`: arg 2 is the sub-subcommand.
# For `docker <sub>`: arg 1 is the subcommand.
# Read-only commands exit 0 silently; spawn commands also exit 0 (we don't
# want hooks to fail because of missing containers) but we log the event.
_DOCKER_SHIM_BODY = r"""#!/usr/bin/env bash
# Fake docker binary installed by tests/contracts/test_self_install_no_container_spawn.py
invocations_log="{invocations_log}"
spawns_log="{spawns_log}"

# Log full argv, one line per call, space-separated, quoted.
printf 'docker' >> "$invocations_log"
for arg in "$@"; do
  printf ' %q' "$arg" >> "$invocations_log"
done
printf '\n' >> "$invocations_log"

sub="${{1:-}}"
sub2="${{2:-}}"

is_spawn="no"
case "$sub" in
  compose)
    case "$sub2" in
      up|start|run|exec) is_spawn="yes" ;;
    esac
    ;;
  run|start|exec)
    is_spawn="yes"
    ;;
esac

if [ "$is_spawn" = "yes" ]; then
  # Prefix with invoking hook name if available via env
  hook_name="${{DOCKER_SHIM_HOOK:-unknown}}"
  printf '%s\t' "$hook_name" >> "$spawns_log"
  printf 'docker' >> "$spawns_log"
  for arg in "$@"; do
    printf ' %q' "$arg" >> "$spawns_log"
  done
  printf '\n' >> "$spawns_log"
fi

# Emit minimal plausible output so hooks don't error out on parsing
case "$sub" in
  info|version) echo "Server: stub"; echo "Version: 0.0-stub" ;;
  ps) ;;  # empty is fine
  compose)
    case "$sub2" in
      ps) echo "" ;;
      config) echo "{{\"services\": {{}}}}" ;;
    esac
    ;;
esac

exit 0
"""


def _run_hook_under_shim(
    hook_path: Path,
    bin_dir: Path,
    tmp_path: Path,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["DOCKER_SHIM_HOOK"] = str(
        hook_path.relative_to(_repo_root())
    )
    env["CLAUDE_PROJECT_DIR"] = str(_repo_root())
    # Defensive: never let the test environment auto-start containers.
    env["INFRA_AUTO_START"] = "false"
    env["COS_DISABLE_LLM_FALLBACK"] = "1"
    # Short per-hook timeout — a SessionStart hook should be fast.
    return subprocess.run(
        ["bash", str(hook_path)],
        cwd=_repo_root(),
        env=env,
        capture_output=True,
        timeout=20,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sessionstart_hooks_are_discovered():
    """Sanity: settings.json exposes SessionStart hooks we can enumerate."""
    hooks = _load_sessionstart_hooks()
    assert len(hooks) >= 3, (
        f"Expected at least a few SessionStart hooks; got {len(hooks)}. "
        "Either settings.json has drifted or hook loader regressed."
    )
    # All enumerated hooks exist on disk.
    for hook in hooks:
        assert hook.exists(), f"SessionStart hook missing from disk: {hook}"


def test_self_install_no_container_spawn(tmp_path):
    """Execute every SessionStart hook under a docker shim and assert no
    unauthorised container spawns occurred."""
    hooks = _load_sessionstart_hooks()
    bin_dir, invocations_log, spawns_log = _install_shim(tmp_path)
    allowlist = _load_allowlist()

    # Always also exercise self-install.sh even if hypothetically de-registered.
    self_install = _repo_root() / "hooks" / "self-install.sh"
    if self_install.exists() and self_install not in hooks:
        hooks.insert(0, self_install)

    for hook in hooks:
        if hook.name in _LAUNCHER_HOOKS:
            # Launcher hooks detach background processes that the shim cannot
            # supervise. Run a bash syntax check only.
            syntax = subprocess.run(
                ["bash", "-n", str(hook)],
                capture_output=True, text=True, timeout=5,
            )
            assert syntax.returncode == 0, (
                f"{hook.relative_to(_repo_root())} failed bash syntax check: "
                f"{syntax.stderr}"
            )
            continue
        try:
            _run_hook_under_shim(hook, bin_dir, tmp_path)
        except subprocess.TimeoutExpired:
            pytest.fail(
                f"Hook {hook.relative_to(_repo_root())} timed out under docker "
                "shim. A SessionStart hook should complete in <20s; a hang "
                "may indicate an unguarded subprocess."
            )

    # Evaluate the spawn log.
    spawns = [
        line for line in spawns_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    violations = []
    for entry in spawns:
        # format: <hook_path>\t<argv...>
        if "\t" not in entry:
            violations.append(("<unknown>", entry))
            continue
        hook_name, argv = entry.split("\t", 1)
        if hook_name in allowlist:
            continue
        violations.append((hook_name, argv))

    assert not violations, (
        "SessionStart hooks spawned Docker containers without allowlist entry.\n"
        "Catalog doctrine: reference stacks are opt-in; SessionStart must not\n"
        "implicitly start containers.\n\n"
        "Violations:\n"
        + "\n".join(f"  {hook} -> {argv}" for hook, argv in violations)
        + "\n\nFix by either (a) removing the spawn from the hook, or "
        "(b) adding it to tests/contracts/docker_spawn_allowlist.txt with "
        "a written justification."
    )


def test_shim_catches_spawn_in_negative_case(tmp_path):
    """Self-test: seed a fake hook that spawns `docker compose up` and verify
    the shim+allowlist machinery catches it."""
    bin_dir, invocations_log, spawns_log = _install_shim(tmp_path)
    fake_hook_dir = tmp_path / "fake-hooks"
    fake_hook_dir.mkdir()
    fake_hook = fake_hook_dir / "bad-hook.sh"
    fake_hook.write_text(
        "#!/usr/bin/env bash\n"
        "docker compose up xyz\n"
        "docker ps\n"
        "docker run --rm busybox true\n",
        encoding="utf-8",
    )
    fake_hook.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["DOCKER_SHIM_HOOK"] = "fake-hooks/bad-hook.sh"
    subprocess.run(
        ["bash", str(fake_hook)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        timeout=10,
        check=True,
    )

    invocations = invocations_log.read_text(encoding="utf-8").splitlines()
    spawns = spawns_log.read_text(encoding="utf-8").splitlines()

    assert len(invocations) == 3, (
        f"Expected 3 docker invocations, got {len(invocations)}: {invocations}"
    )
    # compose up + run → 2 spawns; ps is read-only → not counted
    assert len(spawns) == 2, (
        f"Expected 2 spawn entries (compose up, run), got {len(spawns)}: {spawns}"
    )
    assert all("fake-hooks/bad-hook.sh" in s for s in spawns), (
        f"Spawn entries missing hook attribution: {spawns}"
    )
    assert any("compose up" in s for s in spawns), spawns
    assert any(" run " in s for s in spawns), spawns


def test_allowlist_file_exists_and_is_parseable():
    path = Path(__file__).parent / "docker_spawn_allowlist.txt"
    assert path.exists(), f"allowlist file missing: {path}"
    # Should parse (may be empty of actual entries).
    allowed = _load_allowlist()
    assert isinstance(allowed, set)
