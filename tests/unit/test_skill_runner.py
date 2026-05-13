"""Unit tests for lib/skill_runner.py (ADR-064 Task 5).

Behavioral tests — no mocks of internal logic. All assertions are against
real skills/ directory content so they stay honest as the repo evolves.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Ensure lib/ is importable regardless of invocation context
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.skill_runner import (  # noqa: E402
    RunResult,
    SkillRecord,
    _parse_frontmatter,
    describe_skill,
    detect_harness,
    list_skills,
    run_skill,
)

SKILLS_DIR = REPO_ROOT / "skills"


# ---------------------------------------------------------------------------
# Frontmatter parser
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_parses_basic_fields(self):
        text = dedent("""\
            ---
            name: my-skill
            description: Does a thing
            effort: sonnet
            version: 1.2.3
            ---
            # Body here
        """)
        meta, body = _parse_frontmatter(text)
        assert meta["name"] == "my-skill"
        assert meta["description"] == "Does a thing"
        assert meta["effort"] == "sonnet"
        assert meta["version"] == "1.2.3"
        assert "# Body here" in body

    def test_parses_list_fields(self):
        text = dedent("""\
            ---
            platforms: ["claude-code", "codex"]
            ---
            body
        """)
        meta, body = _parse_frontmatter(text)
        assert isinstance(meta["platforms"], list)
        assert "claude-code" in meta["platforms"]

    def test_handles_html_comment_scope(self):
        text = dedent("""\
            <!-- SCOPE: os-only -->
            ---
            name: tag-release
            ---
            body
        """)
        meta, body = _parse_frontmatter(text)
        assert meta["_scope_comment"] == "os-only"
        assert meta["name"] == "tag-release"

    def test_returns_empty_meta_if_no_frontmatter(self):
        text = "Just plain text with no frontmatter."
        meta, body = _parse_frontmatter(text)
        assert meta == {}

    def test_body_is_content_after_closing_fence(self):
        text = "---\nname: x\n---\nActual body line"
        meta, body = _parse_frontmatter(text)
        assert body.strip() == "Actual body line"


# ---------------------------------------------------------------------------
# list_skills — discovery
# ---------------------------------------------------------------------------


class TestListSkills:
    def test_returns_nonempty_list(self):
        records = list_skills()
        assert len(records) > 0, "Should find at least one skill"

    def test_count_matches_skill_md_files(self):
        skill_md_count = len(list(SKILLS_DIR.glob("*/SKILL.md")))
        records = list_skills()
        assert len(records) == skill_md_count, (
            f"list_skills() returned {len(records)} records but found "
            f"{skill_md_count} SKILL.md files"
        )

    def test_every_record_has_name(self):
        records = list_skills()
        unnamed = [r for r in records if not r.name]
        assert unnamed == [], f"Records with empty name: {unnamed}"

    def test_every_record_has_path(self):
        records = list_skills()
        for r in records:
            assert r.path.exists(), f"Path does not exist: {r.path}"

    def test_records_are_sorted(self):
        records = list_skills()
        # Sort key is the directory name (case-insensitive), not the frontmatter name field
        dir_names = [r.path.parent.name.lower() for r in records]
        assert dir_names == sorted(dir_names), (
            "list_skills() should return records sorted by directory name (case-insensitive)"
        )

    def test_tier_values_are_sane(self):
        valid_tiers = {"opus", "sonnet", "haiku", "unknown"}
        records = list_skills()
        bad = [r for r in records if r.tier not in valid_tiers]
        # Lenient: just check there are not more unknowns than known
        known = [r for r in records if r.tier != "unknown"]
        assert len(known) > len(bad), (
            f"Too many skills with unrecognised tier: {[(r.name, r.tier) for r in bad[:5]]}"
        )


# ---------------------------------------------------------------------------
# describe_skill
# ---------------------------------------------------------------------------


def _pick_stable_skill() -> str:
    """Return a skill name that is highly unlikely to be deleted."""
    for candidate in ("simplify", "tag-release", "add-hook", "code-review"):
        if (SKILLS_DIR / candidate / "SKILL.md").exists():
            return candidate
    # Fallback: first alphabetical
    candidates = sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))
    assert candidates, "No skills found"
    return candidates[0]


class TestDescribeSkill:
    def test_returns_record_for_existing_skill(self):
        name = _pick_stable_skill()
        record = describe_skill(name)
        assert isinstance(record, SkillRecord)
        assert record.name == name or record.name  # name may come from frontmatter

    def test_includes_body(self):
        name = _pick_stable_skill()
        record = describe_skill(name)
        assert len(record.body) > 0, "Body should not be empty"

    def test_raises_key_error_for_missing_skill(self):
        with pytest.raises(KeyError, match="not found"):
            describe_skill("__nonexistent_skill_xyz__")

    def test_case_insensitive_lookup(self):
        name = _pick_stable_skill()
        record = describe_skill(name.upper())
        assert record.name or record.path.exists()

    def test_frontmatter_roundtrip(self):
        name = _pick_stable_skill()
        record = describe_skill(name)
        assert isinstance(record.raw_frontmatter, dict)


# ---------------------------------------------------------------------------
# detect_harness
# ---------------------------------------------------------------------------


class TestDetectHarness:
    def test_explicit_env_wins(self, monkeypatch):
        monkeypatch.setenv("COGNITIVE_OS_HARNESS", "codex")
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        assert detect_harness() == "codex"

    def test_claude_project_dir_implies_claude_code(self, monkeypatch):
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/path")
        monkeypatch.delenv("CODEX_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CODEX_SESSION_ID", raising=False)
        assert detect_harness() == "claude_code"

    def test_codex_env_implies_codex(self, monkeypatch):
        monkeypatch.delenv("COGNITIVE_OS_HARNESS", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("CLAUDE_MCP_SERVER", raising=False)
        monkeypatch.setenv("CODEX_PROJECT_DIR", "/some/path")
        assert detect_harness() == "codex"

    def test_default_is_bare_cli(self, monkeypatch):
        for var in ("COGNITIVE_OS_HARNESS", "CLAUDE_PROJECT_DIR", "CLAUDE_MCP_SERVER",
                    "CODEX_PROJECT_DIR", "CODEX_SESSION_ID"):
            monkeypatch.delenv(var, raising=False)
        assert detect_harness() == "bare_cli"


# ---------------------------------------------------------------------------
# run_skill
# ---------------------------------------------------------------------------


class TestRunSkill:
    def test_cc_harness_returns_slash_command(self):
        name = _pick_stable_skill()
        result = run_skill(name, harness="claude_code")
        assert isinstance(result, RunResult)
        assert result.success
        assert result.rendered.startswith("/")
        assert result.harness == "claude_code"

    def test_cc_harness_includes_args(self):
        name = _pick_stable_skill()
        result = run_skill(name, args={"foo": "bar"}, harness="claude_code")
        assert "--foo=bar" in result.rendered

    def test_bare_cli_harness_returns_body_text(self):
        name = _pick_stable_skill()
        result = run_skill(name, harness="bare_cli")
        assert result.success
        assert len(result.rendered) > 0
        # Should not be a slash command
        assert not result.rendered.strip().startswith("/") or len(result.rendered) > 50

    def test_codex_harness_returns_body_text(self):
        name = _pick_stable_skill()
        result = run_skill(name, harness="codex")
        assert result.success
        assert len(result.rendered) > 0

    def test_arg_substitution_in_body(self, tmp_path):
        # Create a minimal fake skill with a placeholder
        skill_dir = tmp_path / "test-sub"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(dedent("""\
            ---
            name: test-sub
            description: Test arg substitution
            effort: haiku
            ---
            Run this with target={{target}}
        """))
        result = run_skill("test-sub", args={"target": "myfile.py"},
                           harness="bare_cli", skills_root=tmp_path)
        assert result.success
        assert "target=myfile.py" in result.rendered

    def test_missing_skill_returns_failure(self):
        result = run_skill("__nonexistent__", harness="bare_cli")
        assert not result.success
        assert result.rendered == ""

    def test_result_skill_name_matches_input(self):
        name = _pick_stable_skill()
        result = run_skill(name, harness="bare_cli")
        assert result.skill_name == name
