"""Integration tests for bin/cos-skill CLI (ADR-064 Task 5).

These tests shell out to the actual binary so they catch path, shebang, and
invocation issues that pure unit tests miss.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
COS_SKILL = REPO_ROOT / "bin" / "cos-skill"
SKILLS_DIR = REPO_ROOT / "skills"


def run(*args: str, **kwargs) -> subprocess.CompletedProcess:
    """Run cos-skill with the given subcommand + args."""
    cmd = [str(COS_SKILL)] + list(args)
    env_extras = {"COGNITIVE_OS_PROJECT_DIR": str(REPO_ROOT)}
    import os
    env = {**os.environ, **env_extras}
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------


class TestCosSkillBinary:
    def test_binary_is_executable(self):
        assert COS_SKILL.exists(), f"bin/cos-skill not found at {COS_SKILL}"
        assert os.access(str(COS_SKILL), os.X_OK), "bin/cos-skill is not executable"

    def test_help_exits_zero(self):
        result = run("--help")
        assert result.returncode == 0

    def test_no_args_exits_zero(self):
        # --help is default for no args
        result = run()
        assert result.returncode == 0


import os


# ---------------------------------------------------------------------------
# list subcommand
# ---------------------------------------------------------------------------


class TestListSubcommand:
    def test_exits_zero(self):
        result = run("list")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_prints_header(self):
        result = run("list")
        output = result.stdout
        assert "NAME" in output
        assert "TIER" in output
        assert "DESCRIPTION" in output

    def test_output_row_count_matches_skill_md_files(self):
        skill_md_count = len(list(SKILLS_DIR.glob("*/SKILL.md")))
        result = run("list")
        assert result.returncode == 0
        # Subtract 2 header lines
        data_lines = [ln for ln in result.stdout.splitlines()
                      if ln.strip() and not ln.startswith("-") and not ln.startswith("NAME")]
        assert len(data_lines) == skill_md_count, (
            f"Expected {skill_md_count} skill rows, got {len(data_lines)}"
        )

    def test_json_mode_produces_valid_json(self):
        result = run("list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0
        # Spot-check first record fields
        first = data[0]
        assert "name" in first
        assert "tier" in first
        assert "description" in first

    def test_json_count_matches_skill_md_files(self):
        skill_md_count = len(list(SKILLS_DIR.glob("*/SKILL.md")))
        result = run("list", "--json")
        data = json.loads(result.stdout)
        assert len(data) == skill_md_count


# ---------------------------------------------------------------------------
# describe subcommand
# ---------------------------------------------------------------------------


def _pick_stable_skill() -> str:
    for candidate in ("simplify", "tag-release", "add-hook", "code-review"):
        if (SKILLS_DIR / candidate / "SKILL.md").exists():
            return candidate
    candidates = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
    assert candidates, "No skills in repository"
    return candidates[0]


class TestDescribeSubcommand:
    def test_exits_zero_for_existing_skill(self):
        name = _pick_stable_skill()
        result = run("describe", name)
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_output_contains_name(self):
        name = _pick_stable_skill()
        result = run("describe", name)
        assert name in result.stdout or name.replace("-", "") in result.stdout.lower()

    def test_output_contains_tier_label(self):
        name = _pick_stable_skill()
        result = run("describe", name)
        assert "Tier:" in result.stdout or "tier" in result.stdout.lower()

    def test_json_mode_valid(self):
        name = _pick_stable_skill()
        result = run("describe", name, "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["name"] == name or data.get("name")
        assert "body_preview" in data

    def test_missing_skill_exits_nonzero(self):
        result = run("describe", "__nonexistent_skill_xyz__")
        assert result.returncode != 0

    def test_body_section_present(self):
        name = _pick_stable_skill()
        result = run("describe", name)
        # Either "--- Body ---" separator or a non-trivial block of text
        assert len(result.stdout) > 200


# ---------------------------------------------------------------------------
# run subcommand
# ---------------------------------------------------------------------------


class TestRunSubcommand:
    def test_exits_zero_with_bare_cli_harness(self):
        name = _pick_stable_skill()
        result = run("run", name, "--harness=bare_cli")
        assert result.returncode == 0, f"stderr: {result.stderr}"

    def test_output_is_nonempty_for_bare_cli(self):
        name = _pick_stable_skill()
        result = run("run", name, "--harness=bare_cli")
        assert len(result.stdout.strip()) > 0

    def test_cc_harness_emits_slash_command(self):
        name = _pick_stable_skill()
        result = run("run", name, "--harness=claude_code")
        assert result.returncode == 0
        assert result.stdout.strip().startswith("/"), (
            f"Expected slash-command, got: {result.stdout[:80]!r}"
        )

    def test_missing_skill_exits_nonzero(self):
        result = run("run", "__nonexistent__", "--harness=bare_cli")
        assert result.returncode != 0

    def test_unknown_subcommand_exits_nonzero(self):
        result = run("frobnicate")
        assert result.returncode != 0
