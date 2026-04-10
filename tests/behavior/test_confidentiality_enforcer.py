"""Behavior tests for hooks/confidentiality-enforcer.sh.

Validates that the hook correctly:
- Blocks writes with protected terms in docs/markdown files
- Passes clean doc files
- Skips source code files (not scannable paths)
- Blocks external project path references in docs
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior


class TestConfidentialityEnforcer:
    """Tests for hooks/confidentiality-enforcer.sh."""

    # ------------------------------------------------------------------
    # C1: protected term in a doc file → BLOCK
    # ------------------------------------------------------------------

    def test_blocks_write_with_protected_term_in_docs(self, run_hook, cognitive_os_env):
        """Hook must block writes that contain a protected term in a doc file."""
        project_dir: Path = cognitive_os_env["project_dir"]
        cos_dir: Path = cognitive_os_env["cos_dir"]

        # Create confidentiality config with a protected project name
        config = cos_dir / "confidentiality.yaml"
        config.write_text("project_names:\n  - project-x\n")

        # Create a docs file containing the protected term
        docs_dir = project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        target_file = docs_dir / "context.md"
        target_file.write_text("# Context\n\nExtraído de project-x architecture.\n")

        stdin_payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_file)},
        })

        result = run_hook(
            "confidentiality-enforcer.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (BLOCK) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # C2: clean doc file → PASS
    # ------------------------------------------------------------------

    def test_passes_clean_docs(self, run_hook, cognitive_os_env):
        """Hook must pass when the doc file contains no violations."""
        project_dir: Path = cognitive_os_env["project_dir"]
        cos_dir: Path = cognitive_os_env["cos_dir"]

        config = cos_dir / "confidentiality.yaml"
        config.write_text("project_names:\n  - project-x\n")

        docs_dir = project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        target_file = docs_dir / "clean.md"
        target_file.write_text("# Architecture\n\nWe use microservices architecture.\n")

        stdin_payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_file)},
        })

        result = run_hook(
            "confidentiality-enforcer.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 (PASS) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # C3: source code file → SKIP (not scannable)
    # ------------------------------------------------------------------

    def test_skips_source_code_files(self, run_hook, cognitive_os_env):
        """Hook must not scan source code files (.go, .py, .ts, etc.)."""
        project_dir: Path = cognitive_os_env["project_dir"]
        cos_dir: Path = cognitive_os_env["cos_dir"]

        config = cos_dir / "confidentiality.yaml"
        config.write_text("project_names:\n  - project-x\n")

        src_dir = project_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        target_file = src_dir / "handler.go"
        target_file.write_text(
            'package main\n\n// basado en project-x\nfunc main() {}\n'
        )

        stdin_payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": str(target_file)},
        })

        result = run_hook(
            "confidentiality-enforcer.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 (SKIP source) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # C4: external project path in docs → BLOCK
    # ------------------------------------------------------------------

    def test_blocks_external_project_path_in_docs(self, run_hook, cognitive_os_env):
        """Hook must block docs that reference an external project path."""
        project_dir: Path = cognitive_os_env["project_dir"]
        cos_dir: Path = cognitive_os_env["cos_dir"]

        # Minimal confidentiality config (no protected terms needed —
        # external path detection is always active)
        config = cos_dir / "confidentiality.yaml"
        config.write_text("project_names: []\n")

        docs_dir = project_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        target_file = docs_dir / "arch.md"
        # Reference a path that is NOT the current project
        target_file.write_text(
            "# Architecture\n\nSee /Users/<fixture-user>/Projects/<fixture-project>/patterns/ for details.\n"
        )

        # Set CLAUDE_PROJECT_DIR to a different project path so the reference is external
        env = dict(cognitive_os_env["env"])
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)

        stdin_payload = json.dumps({
            "tool_name": "Edit",
            "tool_input": {"file_path": str(target_file)},
        })

        result = run_hook(
            "confidentiality-enforcer.sh",
            env=env,
            stdin=stdin_payload,
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (BLOCK external path) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # ------------------------------------------------------------------
    # Extra: non-Edit/Write tool → SKIP
    # ------------------------------------------------------------------

    def test_skips_non_write_tools(self, run_hook, cognitive_os_env):
        """Hook must silently pass for tools other than Edit and Write."""
        stdin_payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "echo hello"},
        })

        result = run_hook(
            "confidentiality-enforcer.sh",
            env=cognitive_os_env["env"],
            stdin=stdin_payload,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
