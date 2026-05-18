"""
Unit tests for install-skill and install-hook skill SKILL.md files.
Validates frontmatter completeness, routing patterns, and structural integrity.
"""
import pathlib
import re
import pytest
import stat
import subprocess
import tempfile

PROJECT_ROOT = pathlib.Path(__file__).parents[2]
SKILLS_DIR = PROJECT_ROOT / "skills"


def load_frontmatter(skill_name: str) -> dict:
    """Extract raw frontmatter fields from SKILL.md as a simple dict."""
    skill_md = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_md.exists(), f"SKILL.md not found: {skill_md}"
    text = skill_md.read_text()

    # Extract YAML front matter between --- delimiters
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    assert m, f"No valid frontmatter found in {skill_md}"
    fm_text = m.group(1)

    # Minimal parse: just extract top-level string fields
    fields: dict = {}
    for line in fm_text.splitlines():
        kv = re.match(r"^(\w[\w_-]*):\s*(.+)$", line)
        if kv:
            fields[kv.group(1)] = kv.group(2).strip("'\"")
    return fields


def get_skill_md_text(skill_name: str) -> str:
    return (SKILLS_DIR / skill_name / "SKILL.md").read_text()


# ---------------------------------------------------------------------------
# Parametrize over both new skills
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("skill_name", ["install-skill", "install-hook"])
class TestInstallSkillFrontmatter:
    def test_skill_md_exists(self, skill_name):
        assert (SKILLS_DIR / skill_name / "SKILL.md").exists()

    def test_has_name_field(self, skill_name):
        fm = load_frontmatter(skill_name)
        assert "name" in fm, "frontmatter must have 'name'"
        assert fm["name"] == skill_name

    def test_has_description_field(self, skill_name):
        fm = load_frontmatter(skill_name)
        assert "description" in fm, "frontmatter must have 'description'"
        assert len(fm["description"]) > 10, "description must be non-trivial"

    def test_has_version_field(self, skill_name):
        fm = load_frontmatter(skill_name)
        assert "version" in fm, "frontmatter must have 'version'"
        assert re.match(r"\d+\.\d+\.\d+", fm["version"]), "version must be semver"

    def test_has_audience_field(self, skill_name):
        fm = load_frontmatter(skill_name)
        assert "audience" in fm, "frontmatter must have 'audience'"
        assert fm["audience"] in ("os", "project", "both", "os-dev")

    def test_has_summary_line(self, skill_name):
        fm = load_frontmatter(skill_name)
        assert "summary_line" in fm, "frontmatter must have 'summary_line'"

    def test_scope_comment_present(self, skill_name):
        text = get_skill_md_text(skill_name)
        assert "<!-- SCOPE:" in text, "SKILL.md must declare <!-- SCOPE: ... -->"

    def test_trigger_section_present(self, skill_name):
        text = get_skill_md_text(skill_name)
        assert "## Trigger" in text or "triggers:" in text, (
            "SKILL.md must have a Trigger section or triggers frontmatter"
        )

    def test_when_not_to_use_present(self, skill_name):
        text = get_skill_md_text(skill_name)
        assert "When NOT to use" in text, (
            "SKILL.md must have a 'When NOT to use' section for clarity"
        )

    def test_steps_section_present(self, skill_name):
        text = get_skill_md_text(skill_name)
        assert "## Steps" in text, "SKILL.md must have a ## Steps section"

    def test_cross_references_present(self, skill_name):
        text = get_skill_md_text(skill_name)
        assert "Cross-reference" in text or "cross-reference" in text, (
            "SKILL.md should have a Cross-references section"
        )

    def test_routing_pattern_for_slash_command(self, skill_name):
        text = get_skill_md_text(skill_name)
        # Should mention the slash command pattern
        assert f"/{skill_name}" in text, (
            f"SKILL.md should reference the /{skill_name} slash command"
        )


@pytest.mark.parametrize("skill_name", ["install-skill", "install-hook"])
class TestInstallSkillSymlink:
    def test_symlink_exists(self, skill_name):
        link = PROJECT_ROOT / ".claude" / "skills" / skill_name
        assert link.exists(), f".claude/skills/{skill_name} symlink does not exist or is broken"

    def test_symlink_resolves_to_skill_md(self, skill_name):
        link = PROJECT_ROOT / ".claude" / "skills" / skill_name / "SKILL.md"
        assert link.exists(), (
            f".claude/skills/{skill_name}/SKILL.md not reachable through symlink"
        )


class TestInstallSkillBackingScript:
    def test_cos_install_skill_exists(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-skill"
        assert script.exists(), "scripts/cos-install-skill must exist"

    def test_cos_install_skill_executable(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-skill"
        assert script.stat().st_mode & 0o111, "scripts/cos-install-skill must be executable"

    def test_cos_install_skill_shebang(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-skill"
        first_line = script.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env bash", (
            "cos-install-skill must have #!/usr/bin/env bash shebang"
        )

    def test_cos_install_skill_scope_header(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-skill").read_text()
        assert "# SCOPE: os-only" in content

    def test_cos_install_skill_dry_run_flag(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-skill").read_text()
        assert "--dry-run" in content

    def test_cos_install_hook_exists(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-hook"
        assert script.exists(), "scripts/cos-install-hook must exist"

    def test_cos_install_hook_executable(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-hook"
        assert script.stat().st_mode & 0o111, "scripts/cos-install-hook must be executable"

    def test_cos_install_hook_shebang(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-hook"
        first_line = script.read_text().splitlines()[0]
        assert first_line == "#!/usr/bin/env bash"

    def test_cos_install_hook_scope_header(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-hook").read_text()
        assert "# SCOPE: os-only" in content

    def test_cos_install_hook_event_flag(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-hook").read_text()
        assert "--event" in content

    def test_cos_install_hook_dry_run_flag(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-hook").read_text()
        assert "--dry-run" in content

    def test_cos_install_hook_never_writes_settings_json_directly(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-hook").read_text()
        # Must not reference settings.json directly for writing
        assert "settings.json" not in content, (
            "cos-install-hook must not write settings.json directly — "
            "use apply-efficiency-profile.sh"
        )

    def test_cos_install_hook_dry_run_does_not_chmod_before_exit(self):
        script = PROJECT_ROOT / "scripts" / "cos-install-hook"
        with tempfile.TemporaryDirectory(prefix=".cos-install-hook-test-", dir=PROJECT_ROOT) as tmp:
            hook_path = pathlib.Path(tmp) / "dry-run-sample.sh"
            hook_path.write_text(
                "#!/usr/bin/env bash\n"
                "# SCOPE: both\n"
                "# EVENT: Stop\n"
                "set -euo pipefail\n"
                "exit 0\n",
                encoding="utf-8",
            )
            hook_path.chmod(0o644)

            result = subprocess.run(
                [
                    str(script),
                    "dry-run-sample",
                    "--source",
                    str(hook_path),
                    "--event",
                    "Stop",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
                timeout=30,
            )

            assert result.returncode == 0, result.stderr
            assert not hook_path.stat().st_mode & stat.S_IXUSR, (
                "cos-install-hook --dry-run must not chmod source hooks"
            )

    def test_cos_install_hook_rollback_uses_backup_not_git_checkout(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-hook").read_text()
        assert "COSYAML_BACKUP" in content
        assert "git -C \"$PROJECT_ROOT\" checkout -- cognitive-os.yaml" not in content

    def test_cos_install_skill_creates_driver_directory(self):
        content = (PROJECT_ROOT / "scripts" / "cos-install-skill").read_text()
        assert 'mkdir -p "$(dirname "$SYMLINK_TARGET")"' in content


class TestInstallSkillDryRun:
    """Behavioral tests: dry-run must not create any files."""

    def test_dry_run_does_not_create_symlink(self, tmp_path):
        """
        Use the real project's install-recommended skill directory as a known-good
        source so the script's PROJECT_ROOT scope check passes (source is inside
        the same project tree as the script).
        """
        import subprocess

        # Use a real skill that already exists in the project as the source
        # (we pass --source pointing inside the real project root, so the scope
        # check passes, but we also pass a fake target name to avoid collision
        # with an already-installed skill).
        real_source = PROJECT_ROOT / "skills" / "install-recommended"
        assert real_source.exists(), "install-recommended skill must exist as test fixture"

        # Attempt to install under a name that does NOT exist yet as a symlink
        target_name = "_test-dry-run-install-skill"
        target_link = PROJECT_ROOT / ".claude" / "skills" / target_name

        script = PROJECT_ROOT / "scripts" / "cos-install-skill"
        result = subprocess.run(
            [str(script), target_name, "--source", str(real_source), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"dry-run failed:\n{result.stderr}"
        # Symlink must NOT have been created
        assert not target_link.exists(), "dry-run must not create the symlink"
        assert "[dry-run]" in result.stdout
