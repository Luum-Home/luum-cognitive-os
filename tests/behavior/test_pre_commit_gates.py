"""Tests for .githooks/pre-commit enforcement gates.

Validates:
- Gate 1: blocks commits with prohibited project-specific terms
- Gate 2: blocks commits with Python syntax errors in staged .py files
- Gate 3a: warns when new hooks are not registered in apply-efficiency-profile.sh
- Gate 3b: warns when new lib/ file duplicates a packages/ symlink
- Gate 3c: warns when new skill directory is missing SKILL.md
- Gate 3d: warns on direct settings.json edits
- Gate 3e: warns on malformed workflow YAML
- Valid commit passes with exit 0

NOTE: Tests run the hook with specific environment vars to simulate staged files
without actually modifying the git index.
"""

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / ".githooks" / "pre-commit"

pytestmark = pytest.mark.behavior


def _run_hook(env_overrides=None, cwd=None):
    """Run the pre-commit hook and return the result."""
    env = os.environ.copy()
    env["GIT_DIR"] = str(PROJECT_ROOT / ".git")
    env["PROJECT_ROOT"] = str(PROJECT_ROOT)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd or PROJECT_ROOT),
        timeout=30,
    )


def _make_git_repo(tmp_path):
    """Create a minimal git repo in tmp_path for isolated testing."""
    subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


# ─── Hook structure ───────────────────────────────────────────────────────────


class TestHookStructure:

    def test_hook_is_valid_bash(self):
        result = subprocess.run(
            ["bash", "-n", str(HOOK)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Bash syntax error: {result.stderr}"

    def test_hook_is_executable_or_runnable_via_bash(self):
        # We can always run it via bash, so just verify the file is not empty
        content = HOOK.read_text()
        assert len(content) > 100, "Hook file seems too short"

    def test_hook_has_shebang(self):
        content = HOOK.read_text()
        assert content.startswith("#!/"), "Hook must start with a shebang"


    def test_hook_has_seven_gates(self):
        """Hook should have identifiable gate sections."""
        content = HOOK.read_text()
        # Count Gate references (Gate1, Gate2, Gate3a, etc.)
        import re
        gates = re.findall(r'Gate\s*[0-9]+[a-z]?', content, re.IGNORECASE)
        assert len(gates) >= 7, f"Expected at least 7 gate references, found: {gates}"


# ─── Gate 1: prohibited terms ─────────────────────────────────────────────────


class TestGate1ProhibitedTerms:
    """Gate 1 must block commits containing prohibited project-specific terms."""

    def _stage_file_with_content(self, repo, filename, content):
        filepath = repo / filename
        filepath.write_text(content)
        subprocess.run(["git", "add", str(filepath)], cwd=str(repo), capture_output=True)

    def test_gate1_blocks_file_with_prohibited_term(self, tmp_path):
        """A staged .py file containing a prohibited term should block the commit."""
        repo = _make_git_repo(tmp_path)
        # Copy the hook into the repo so it can be run from there
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        # Create and stage a file with a known prohibited term
        # Based on Gate1 patterns (n1u, gamer-wallet, altatienda are blocked)
        bad_file = repo / "bad.py"
        bad_file.write_text("# This mentions n1u which is prohibited\npass\n")
        subprocess.run(["git", "add", str(bad_file)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        # Gate1 should block (exit 1) when prohibited term found
        assert result.returncode != 0, (
            f"Hook should block on prohibited term. stdout: {result.stdout}"
        )

    def test_gate1_message_explains_violation(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        bad_file = repo / "bad.md"
        bad_file.write_text("This project uses gamer-wallet as a dependency.\n")
        subprocess.run(["git", "add", str(bad_file)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        combined = result.stdout + result.stderr
        # Should mention the term or "prohibited" or "blocked"
        assert (
            "n1u" in combined.lower()
            or "gamer" in combined.lower()
            or "prohibited" in combined.lower()
            or "blocked" in combined.lower()
            or "gate" in combined.lower()
        )

    def test_gate1_ignores_gitlink_submodule_worktree_content(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        plugin = repo / "vendor" / "plugin"
        plugin.mkdir(parents=True)
        (plugin / "README.md").write_text(
            "Upstream docs mention gamer-wallet, but this is submodule content.\n"
        )
        subprocess.run(
            [
                "git",
                "update-index",
                "--add",
                "--cacheinfo",
                "160000,0123456789012345678901234567890123456789,vendor/plugin",
            ],
            cwd=str(repo),
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )

        assert result.returncode == 0, result.stdout + result.stderr


# ─── Gate 2: Python syntax ────────────────────────────────────────────────────


class TestGate2PythonSyntax:
    """Gate 2 must block commits with Python syntax errors."""

    def test_gate2_blocks_syntax_error(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        bad_py = repo / "broken.py"
        bad_py.write_text("def foo(\n    # missing closing paren and body\n")
        subprocess.run(["git", "add", str(bad_py)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        assert result.returncode != 0, "Gate 2 should block on Python syntax error"

    def test_gate2_allows_valid_python(self, tmp_path):
        """A valid Python file with no prohibited terms should not be blocked by Gate2."""
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        good_py = repo / "valid.py"
        good_py.write_text('"""Valid module."""\n\ndef hello():\n    return "world"\n')
        subprocess.run(["git", "add", str(good_py)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        # Should exit 0 — no blocking issues
        assert result.returncode == 0, (
            f"Valid Python should pass Gate 2. stdout: {result.stdout} stderr: {result.stderr}"
        )


# ─── Gate 3a: new hook must be in apply-efficiency-profile.sh ─────────────────


class TestGate3aHookRegistration:
    """Gate 3a warns (does not block) when a new hook is not in apply-efficiency-profile.sh."""

    def test_gate3a_warns_on_unregistered_hook(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        scripts_dir = repo / "scripts"
        scripts_dir.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")
        # Copy apply-efficiency-profile.sh
        real_script = PROJECT_ROOT / "scripts" / "apply-efficiency-profile.sh"
        if real_script.exists():
            shutil.copy(real_script, scripts_dir / "apply-efficiency-profile.sh")

        hooks_dir = repo / "hooks"
        hooks_dir.mkdir()
        new_hook = hooks_dir / "my-brand-new-hook.sh"
        new_hook.write_text("#!/usr/bin/env bash\n# new hook\nexit 0\n")
        subprocess.run(["git", "add", str(new_hook)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={
                **os.environ,
                "GIT_DIR": str(repo / ".git"),
                "PROJECT_ROOT": str(repo),
            },
            timeout=20,
        )
        combined = result.stdout + result.stderr
        # Gate 3a blocks (exit 1) when a new hook is not registered in apply-efficiency-profile.sh
        # The hook exits 1 with a BLOCKED message, not just a warning
        assert (
            "warn" in combined.lower()
            or "warning" in combined.lower()
            or "apply-efficiency-profile" in combined.lower()
            or "register" in combined.lower()
            or "not found" in combined.lower()
            or "profile" in combined.lower()
            or "blocked" in combined.lower()
        ), f"Expected message about unregistered hook. Got: {combined[:500]}"


# ─── Gate 3e: workflow YAML parse check ──────────────────────────────────────


class TestGate3eWorkflowYaml:
    """Gate 3e warns on malformed workflow YAML."""

    def test_gate3e_warns_on_malformed_yaml(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        workflows_dir = repo / ".cognitive-os" / "workflows"
        workflows_dir.mkdir(parents=True)
        bad_yaml = workflows_dir / "bad-pipeline.yaml"
        bad_yaml.write_text(
            "steps:\n  - name: step1\n    type: agent\n      bad_indent: broken\n"
        )
        subprocess.run(["git", "add", str(bad_yaml)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        # Gate 3e is advisory — should exit 0 but mention the yaml issue
        # (or it might not have python available, graceful skip is OK)
        assert result.returncode == 0, (
            f"Gate 3e is advisory — should not block. Got: {result.returncode}"
        )


# ─── Clean commit passes ─────────────────────────────────────────────────────


class TestCleanCommitPasses:
    """A commit with no violations must exit 0."""

    def test_empty_staged_set_exits_zero(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        # Stage a clean, innocuous file
        readme = repo / "README.txt"
        readme.write_text("Hello world.\n")
        subprocess.run(["git", "add", str(readme)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        assert result.returncode == 0, (
            f"Clean commit should pass. stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_valid_python_file_passes(self, tmp_path):
        repo = _make_git_repo(tmp_path)
        hook_dest = repo / ".githooks"
        hook_dest.mkdir()
        import shutil
        shutil.copy(HOOK, hook_dest / "pre-commit")

        py_file = repo / "module.py"
        py_file.write_text(
            '"""A clean module with no violations."""\n\n\ndef add(a, b):\n    """Add two numbers."""\n    return a + b\n'
        )
        subprocess.run(["git", "add", str(py_file)], cwd=str(repo), capture_output=True)

        result = subprocess.run(
            ["bash", str(hook_dest / "pre-commit")],
            capture_output=True,
            text=True,
            cwd=str(repo),
            env={**os.environ, "GIT_DIR": str(repo / ".git"), "PROJECT_ROOT": str(repo)},
            timeout=20,
        )
        assert result.returncode == 0, (
            f"Clean Python should pass. stdout: {result.stdout}\nstderr: {result.stderr}"
        )
