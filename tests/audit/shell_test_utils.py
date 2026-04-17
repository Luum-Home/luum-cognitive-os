"""Shell test helpers — safe subprocess invocation + throwaway project scaffolding.

Every function here is designed to be SAFE by construction:
  - `run_shell` always uses an explicit `cwd` and `env`; it never inherits
    the developer's live environment beyond what the caller whitelists.
  - `make_throwaway_project` only writes under a caller-supplied `tmp_path`.
  - Timeouts are mandatory and capped at 120 s to prevent hung subprocesses.

These helpers are shared between tests/audit/test_install_scripts.py and any
future audit agent that needs to exercise shell scripts end-to-end.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, Iterable, Optional

# Absolute path to the project root — resolved at import time so the helpers
# can locate shell scripts without relying on the developer's CWD.
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_shell(
    script_path: Path,
    env: Optional[Dict[str, str]] = None,
    cwd: Optional[Path] = None,
    timeout: int = 60,
    args: Optional[Iterable[str]] = None,
    dry_run: bool = False,
) -> subprocess.CompletedProcess:
    """Run a shell script under controlled conditions.

    Parameters
    ----------
    script_path : Path
        Absolute path to the `.sh` file to execute.
    env : dict, optional
        Environment variables to merge on top of a minimal base.  The base
        always contains PATH (from the host) and HOME pointed at `cwd` (or
        tmp) so scripts that touch `$HOME` do NOT touch the developer's real
        home directory.
    cwd : Path, optional
        Working directory.  If None, uses `script_path.parent`.
    timeout : int
        Hard timeout in seconds.  Capped at 120.
    args : iterable of str, optional
        Positional arguments appended after the script path.
    dry_run : bool
        If True, appends `--dry-run` to args if the script supports it.  The
        caller is responsible for knowing whether --dry-run is supported;
        this flag is a convenience.
    """
    if timeout > 120:
        timeout = 120

    cwd = cwd or script_path.parent
    cwd = Path(cwd).resolve()

    # Build a minimal, explicit environment.  HOME is redirected to `cwd` by
    # default so any script that writes to `$HOME/.something` cannot escape
    # the sandbox.  Callers can override by passing env={"HOME": ...}.
    base_env: Dict[str, str] = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(cwd),
        "SHELL": "/bin/bash",
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        # Disable interactivity in any child process.
        "CI": "true",
        "TERM": "dumb",
    }
    if env:
        base_env.update(env)

    argv = ["bash", str(script_path)]
    if args:
        argv.extend(args)
    if dry_run and "--dry-run" not in argv:
        argv.append("--dry-run")

    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env=base_env,
        cwd=str(cwd),
        timeout=timeout,
        check=False,
    )


def bash_syntax_check(script_path: Path, timeout: int = 10) -> subprocess.CompletedProcess:
    """Return the result of `bash -n <script_path>` (syntax-only check)."""
    return subprocess.run(
        ["bash", "-n", str(script_path)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def make_throwaway_project(tmp_path: Path) -> Path:
    """Create a minimal self-hostable project layout under `tmp_path`.

    The layout mirrors what `hooks/self-install.sh` expects to sync FROM.
    It is deliberately small (a few files per synced dir) so tests stay
    fast.  Returns the project root path.

    NOTE: this mirrors the `_setup_full_project` helper in
    tests/behavior/test_self_install.py but is self-contained so that
    tests/audit/ does not depend on behavior/.
    """
    project = tmp_path / "project"
    project.mkdir()

    # --- Marker: hooks/self-install.sh (self-hosting detector) -----------
    hooks_dir = project / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "self-install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (hooks_dir / "session-init.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (hooks_dir / "health.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    # --- Rules -----------------------------------------------------------
    rules_dir = project / "rules"
    rules_dir.mkdir()
    (rules_dir / "RULES-COMPACT.md").write_text("# Compact\n")
    (rules_dir / "adaptive-bypass.md").write_text("# Adaptive Bypass\n")
    (rules_dir / "acceptance-criteria.md").write_text("# AC\n")
    (rules_dir / "trust-score.md").write_text("# Trust\n")
    (rules_dir / "sample.md").write_text("# Sample\n")

    # --- Skills (regression: these names match the ADR-001 ghost list) ---
    for name in ("compose-prompt", "session-backlog", "agent-dashboard"):
        skill = project / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(f"# {name}\n")
    (project / "skills" / "CATALOG.md").write_text("# Catalog\n")

    # --- Squads ----------------------------------------------------------
    squads_dir = project / "squads"
    squads_dir.mkdir()
    (squads_dir / "infra-team.yaml").write_text("name: infra\n")

    # --- Templates -------------------------------------------------------
    tpl_dir = project / "templates"
    tpl_dir.mkdir()
    (tpl_dir / "agent-preamble.md").write_text("# Preamble\n")

    # --- Agents ----------------------------------------------------------
    agents_dir = project / "agents"
    agents_dir.mkdir()
    (agents_dir / "stack-validator.md").write_text("# Stack Validator\n")

    # --- Customizations --------------------------------------------------
    cust_dir = project / "customizations"
    cust_dir.mkdir()
    (cust_dir / "example.yaml").write_text("model: sonnet\n")

    # --- Docs (tree strategy) -------------------------------------------
    docs_dir = project / "docs"
    docs_dir.mkdir()
    (docs_dir / "README.md").write_text("# Docs\n")
    (docs_dir / "architecture.md").write_text("# Architecture\n")

    # --- Infrastructure required by self-install.sh ---------------------
    (project / ".claude").mkdir()
    (project / ".claude" / "settings.json").write_text('{"hooks": {}}\n')
    (project / "cognitive-os.yaml").write_text("version: 1\n")

    # Git hooks scaffolding (check 3/4 in self-install.sh).
    githooks_dir = project / ".githooks"
    githooks_dir.mkdir()
    pre_commit = githooks_dir / "pre-commit"
    pre_commit.write_text("#!/usr/bin/env bash\nexit 0\n")
    pre_commit.chmod(0o755)

    # Initialize git so self-install.sh can persist core.hooksPath.
    subprocess.run(
        ["git", "init", str(project)],
        capture_output=True, check=False, timeout=10,
    )
    subprocess.run(
        ["git", "-C", str(project), "config", "core.hooksPath", ".githooks"],
        capture_output=True, check=False, timeout=10,
    )

    # Workflows dir (check 5).
    (project / ".cognitive-os" / "workflows").mkdir(parents=True, exist_ok=True)

    return project


def count_skills_at(path: Path) -> int:
    """Count direct-child subdirectories (regular OR symlink-to-dir) that
    contain a `SKILL.md` file.  Returns 0 if `path` does not exist.
    """
    if not path.exists():
        return 0
    count = 0
    for entry in path.iterdir():
        # Accept both regular dirs and symlinks that resolve to dirs.
        if not entry.is_dir():
            continue
        if (entry / "SKILL.md").exists():
            count += 1
    return count


def count_symlinks(path: Path) -> int:
    """Return the number of symbolic links at the top level of `path`.
    Returns 0 if `path` does not exist.
    """
    if not path.exists():
        return 0
    return sum(1 for entry in path.iterdir() if entry.is_symlink())


def assert_path_exists(p: Path, label: str = "") -> None:
    """Assertion helper that raises AssertionError with a clear message."""
    if not p.exists():
        raise AssertionError(
            f"expected path to exist{' (' + label + ')' if label else ''}: {p}"
        )


def assert_path_absent(p: Path, label: str = "") -> None:
    """Assertion helper that raises AssertionError with a clear message."""
    if p.exists():
        raise AssertionError(
            f"expected path to be absent{' (' + label + ')' if label else ''}: {p}"
        )


# ---------------------------------------------------------------------------
# Target scripts — the 8 install/update/uninstall scripts under audit.
# ---------------------------------------------------------------------------

TARGET_SCRIPTS = [
    PROJECT_ROOT / "hooks" / "self-install.sh",
    PROJECT_ROOT / "scripts" / "cos-init.sh",
    PROJECT_ROOT / "scripts" / "cos-update.sh",
    PROJECT_ROOT / "scripts" / "auto-update-projects.sh",
    PROJECT_ROOT / "scripts" / "cos-init-global.sh",
    PROJECT_ROOT / "scripts" / "cos-bootstrap.sh",
    PROJECT_ROOT / "scripts" / "uninstall.sh",
    PROJECT_ROOT / "install.sh",
]


def target_script_ids() -> list[str]:
    """Stable pytest IDs for the parameterized target-script list."""
    return [p.relative_to(PROJECT_ROOT).as_posix() for p in TARGET_SCRIPTS]
