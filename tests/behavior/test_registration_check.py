"""Behavior tests for hooks/registration-check.sh.

Validates that the hook:
- Warns (to stderr) when unregistered components are found in the OS repo
- Is completely silent in non-OS-repo projects
- Always exits 0 (advisory, never blocks)
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_os_env(cognitive_os_env: dict) -> dict:
    """Extend a cognitive_os_env fixture to look like the luum-agent-os repo.

    Creates the sentinel file hooks/self-install.sh plus a minimal lib/
    directory with component_registry.py so the hook's guards pass.
    Returns the updated env dict.
    """
    project_dir: Path = cognitive_os_env["project_dir"]

    # Sentinel: makes the hook think we're inside the OS repo
    _write(project_dir / "hooks" / "self-install.sh", "#!/usr/bin/env bash\n")

    # Minimal RULES-COMPACT.md (so detect_unregistered_rules can run)
    _write(
        project_dir / "rules" / "RULES-COMPACT.md",
        "# COS Rules Index\n",
    )

    # Minimal CATALOG.md
    _write(
        project_dir / "skills" / "CATALOG.md",
        "# Catalog\n| Skill | Description | Invoke | Audience |\n",
    )

    # Minimal packages.yaml
    _write(
        project_dir / "packages" / "cos-index" / "index" / "packages.yaml",
        "packages:\n",
    )

    # Minimal apply-efficiency-profile.sh — pre-register self-install.sh so the
    # sentinel file is not itself flagged as unregistered.
    _write(
        project_dir / "scripts" / "apply-efficiency-profile.sh",
        '#!/usr/bin/env bash\n# profile script\nhook_entry "self-install.sh"\n',
    )

    # Copy lib/component_registry.py from the real project so the hook can import it
    import shutil
    real_lib = Path(__file__).resolve().parent.parent.parent / "lib" / "component_registry.py"
    lib_dir = project_dir / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(real_lib, lib_dir / "component_registry.py")

    return cognitive_os_env


# ---------------------------------------------------------------------------
# R9 — warns on unregistered components in OS repo
# ---------------------------------------------------------------------------

class TestRegistrationCheckInOsRepo:
    """Hook warns when unregistered components exist inside the OS repo."""

    def test_warns_on_unregistered_hook(self, run_hook, cognitive_os_env):
        """Hook outputs a WARNING to stderr and exits 0 when an unregistered hook exists."""
        env_data = _make_os_env(cognitive_os_env)
        project_dir: Path = env_data["project_dir"]

        # Add an unregistered hook (not mentioned in apply-efficiency-profile.sh)
        _write(project_dir / "hooks" / "orphan-hook.sh", "#!/usr/bin/env bash\n")

        # The hook reads stdin (standard PreToolUse payload)
        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do some work"},
        })

        result = run_hook(
            "registration-check.sh",
            env=env_data["env"],
            stdin=stdin_payload,
        )

        # Always exits 0 (advisory)
        assert result.returncode == 0, (
            f"Expected exit 0 but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        # Warning appears on stderr
        assert "WARNING" in result.stderr or "REGISTRATION CHECK" in result.stderr, (
            f"Expected a warning on stderr but got: {result.stderr!r}"
        )
        assert "orphan-hook.sh" in result.stderr, (
            f"Expected 'orphan-hook.sh' in stderr but got: {result.stderr!r}"
        )

    def test_exit_0_even_when_warnings_emitted(self, run_hook, cognitive_os_env):
        """Hook must always exit 0 — it is advisory, never blocking."""
        env_data = _make_os_env(cognitive_os_env)
        project_dir: Path = env_data["project_dir"]

        # Multiple unregistered items
        _write(project_dir / "hooks" / "alpha.sh", "#!/usr/bin/env bash\n")
        _write(project_dir / "hooks" / "beta.sh", "#!/usr/bin/env bash\n")
        _write(project_dir / "rules" / "orphan-rule.md", "# Orphan\n")

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Build something"},
        })

        result = run_hook(
            "registration-check.sh",
            env=env_data["env"],
            stdin=stdin_payload,
        )

        assert result.returncode == 0

    def test_silent_when_all_registered(self, run_hook, cognitive_os_env):
        """Hook produces no output when everything is registered."""
        env_data = _make_os_env(cognitive_os_env)
        project_dir: Path = env_data["project_dir"]

        # Add a hook AND register it in the profile script
        _write(project_dir / "hooks" / "known.sh", "#!/usr/bin/env bash\n")
        profile = project_dir / "scripts" / "apply-efficiency-profile.sh"
        existing = profile.read_text()
        profile.write_text(existing + '\nhook_entry "known.sh"\n')

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Do work"},
        })

        result = run_hook(
            "registration-check.sh",
            env=env_data["env"],
            stdin=stdin_payload,
        )

        assert result.returncode == 0
        # stderr should be empty (or at most whitespace) — no warning needed
        assert result.stderr.strip() == "", (
            f"Expected empty stderr but got: {result.stderr!r}"
        )


# ---------------------------------------------------------------------------
# R10 — silent in non-OS-repo projects
# ---------------------------------------------------------------------------

class TestRegistrationCheckInNonOsRepo:
    """Hook is completely silent when NOT inside the luum-agent-os repo."""

    def test_silent_in_non_os_project(self, run_hook, cognitive_os_env):
        """Hook exits 0 with no output when hooks/self-install.sh does NOT exist."""
        # cognitive_os_env creates a tmp project WITHOUT hooks/self-install.sh
        project_dir: Path = cognitive_os_env["project_dir"]

        # Confirm self-install.sh is absent
        assert not (project_dir / "hooks" / "self-install.sh").exists()

        stdin_payload = json.dumps({
            "tool_name": "Agent",
            "tool_input": {"prompt": "Some task in a user project"},
        })

        result = run_hook(
            "registration-check.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )

        assert result.returncode == 0, (
            f"Expected exit 0 but got {result.returncode}.\n"
            f"stderr: {result.stderr}"
        )
        assert result.stdout.strip() == "", (
            f"Expected empty stdout but got: {result.stdout!r}"
        )
        assert result.stderr.strip() == "", (
            f"Expected empty stderr but got: {result.stderr!r}"
        )
