"""Tests for lib/pattern_detector.py — pattern detection engine.

Creates temporary project structures with known issues and verifies
the detector finds them. All tests are behavioral: they exercise the
actual detection logic, not just file existence.
"""
import json
import os
import sys
import textwrap

import pytest

# Ensure lib/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from lib.pattern_detector import DetectedPattern, PatternDetector, _file_exists, _resolve


@pytest.fixture
def detector():
    return PatternDetector()


@pytest.fixture
def tmp_project(tmp_path):
    """Create a minimal project structure for testing."""
    # Create directories
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "__init__.py").write_text("")
    (tmp_path / "hooks").mkdir()
    (tmp_path / "hooks" / "_lib").mkdir()
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / ".claude").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Dead Metadata Detection
# ---------------------------------------------------------------------------
class TestDeadMetadata:
    def test_detects_unused_frontmatter_field(self, detector, tmp_project):
        """A frontmatter field that no code reads should be flagged."""
        skill_dir = tmp_project / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: my-skill
            description: A test skill
            custom-unused-field: true
            ---
            ## Purpose
            Test skill.
        """))
        # No code references 'custom-unused-field'
        (tmp_project / "lib" / "helper.py").write_text("x = 1\n")

        results = detector.detect_dead_metadata(str(tmp_project))

        dead_keys = [r.component for r in results]
        assert "frontmatter.custom-unused-field" in dead_keys
        assert all(r.type == "dead_metadata" for r in results)

    def test_ignores_fields_referenced_by_code(self, detector, tmp_project):
        """A frontmatter field that code reads should NOT be flagged."""
        skill_dir = tmp_project / "skills" / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: my-skill
            description: A test skill
            audience: os
            ---
            ## Purpose
            Test skill.
        """))
        # Code references 'audience'
        (tmp_project / "lib" / "loader.py").write_text(
            'data = fm.get("audience", "both")\n'
        )

        results = detector.detect_dead_metadata(str(tmp_project))
        dead_keys = [r.component for r in results]
        assert "frontmatter.audience" not in dead_keys

    def test_skips_universal_keys(self, detector, tmp_project):
        """Keys like name, description, version are never flagged."""
        skill_dir = tmp_project / "skills" / "basic"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: basic
            description: Basic skill
            version: 1.0.0
            ---
        """))

        results = detector.detect_dead_metadata(str(tmp_project))
        dead_keys = [r.component for r in results]
        assert "frontmatter.name" not in dead_keys
        assert "frontmatter.description" not in dead_keys
        assert "frontmatter.version" not in dead_keys


# ---------------------------------------------------------------------------
# Broken Chains Detection
# ---------------------------------------------------------------------------
class TestBrokenChains:
    def test_detects_broken_python_import(self, detector, tmp_project):
        """An import to a missing local module should be flagged."""
        (tmp_project / "lib" / "caller.py").write_text(
            "from lib.nonexistent_module import something\n"
        )

        results = detector.detect_broken_chains(str(tmp_project))

        broken = [r for r in results if r.type == "broken_chain"]
        assert len(broken) >= 1
        assert any("nonexistent_module" in r.description for r in broken)

    def test_ignores_valid_import(self, detector, tmp_project):
        """An import to an existing module should NOT be flagged."""
        (tmp_project / "lib" / "valid_module.py").write_text("x = 1\n")
        (tmp_project / "lib" / "caller.py").write_text(
            "from lib.valid_module import x\n"
        )

        results = detector.detect_broken_chains(str(tmp_project))
        broken = [r for r in results if "valid_module" in r.description]
        assert len(broken) == 0

    def test_ignores_stdlib_imports(self, detector, tmp_project):
        """Standard library imports should NOT be checked."""
        (tmp_project / "lib" / "stdlib_user.py").write_text(
            "import os\nimport json\nfrom pathlib import Path\n"
        )

        results = detector.detect_broken_chains(str(tmp_project))
        assert len(results) == 0

    def test_detects_broken_hook_reference(self, detector, tmp_project):
        """A settings.json hook pointing to a missing script should be flagged."""
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/ghost-hook.sh"',
                            }
                        ],
                    }
                ]
            }
        }
        (tmp_project / ".claude" / "settings.json").write_text(
            json.dumps(settings, indent=2)
        )

        results = detector.detect_broken_chains(str(tmp_project))
        broken = [r for r in results if r.type == "broken_chain"]
        assert len(broken) >= 1
        assert any("ghost-hook" in r.description for r in broken)

    def test_valid_hook_not_flagged(self, detector, tmp_project):
        """A settings.json hook pointing to an existing script should NOT be flagged."""
        hook_file = tmp_project / "hooks" / "real-hook.sh"
        hook_file.write_text("#!/bin/bash\necho ok\n")

        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "",
                        "hooks": [
                            {
                                "type": "command",
                                "command": 'bash "$CLAUDE_PROJECT_DIR/hooks/real-hook.sh"',
                            }
                        ],
                    }
                ]
            }
        }
        (tmp_project / ".claude" / "settings.json").write_text(
            json.dumps(settings, indent=2)
        )

        results = detector.detect_broken_chains(str(tmp_project))
        broken = [r for r in results if "real-hook" in r.description]
        assert len(broken) == 0


# ---------------------------------------------------------------------------
# Symlink Resolution
# ---------------------------------------------------------------------------
class TestSymlinkResolution:
    def test_symlink_resolved_correctly(self, tmp_path):
        """Symlinks should resolve to their target before existence check."""
        target = tmp_path / "actual_file.py"
        target.write_text("x = 1\n")
        link = tmp_path / "link_file.py"
        link.symlink_to(target)

        assert _file_exists(str(link))
        assert _resolve(str(link)) == str(target.resolve())

    def test_broken_symlink_detected(self, tmp_path):
        """A symlink to a non-existent target should fail existence check."""
        link = tmp_path / "broken_link.py"
        link.symlink_to(tmp_path / "nonexistent.py")

        assert not _file_exists(str(link))

    def test_symlinked_import_not_flagged(self, detector, tmp_project):
        """A valid import via symlink should NOT be flagged as broken."""
        # Create actual file
        actual = tmp_project / "lib" / "real_module.py"
        actual.write_text("y = 2\n")

        # Create symlink to it
        link = tmp_project / "lib" / "aliased_module.py"
        link.symlink_to(actual)

        # Import via symlink name
        (tmp_project / "lib" / "user.py").write_text(
            "from lib.aliased_module import y\n"
        )

        results = detector.detect_broken_chains(str(tmp_project))
        broken = [r for r in results if "aliased_module" in r.description]
        assert len(broken) == 0


# ---------------------------------------------------------------------------
# Phantom Entries Detection
# ---------------------------------------------------------------------------
class TestPhantomEntries:
    def test_detects_phantom_catalog_entry(self, detector, tmp_project):
        """A skill listed in CATALOG.md without SKILL.md should be flagged."""
        catalog = tmp_project / "skills" / "CATALOG.md"
        catalog.write_text(textwrap.dedent("""\
            # Skills Catalog

            | Skill | Description | Invoke | Audience |
            |-------|-------------|--------|----------|
            | ghost-skill | Does not exist | `/ghost` | os |
        """))

        results = detector.detect_phantom_entries(str(tmp_project))
        phantoms = [r for r in results if r.type == "phantom_entry"]
        assert any("ghost-skill" in r.component for r in phantoms)

    def test_valid_catalog_entry_not_flagged(self, detector, tmp_project):
        """A skill listed in CATALOG.md with a SKILL.md should NOT be flagged."""
        skill_dir = tmp_project / "skills" / "real-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: real-skill\n---\n")

        catalog = tmp_project / "skills" / "CATALOG.md"
        catalog.write_text(textwrap.dedent("""\
            # Skills Catalog

            | Skill | Description | Invoke | Audience |
            |-------|-------------|--------|----------|
            | real-skill | Exists | `/real` | os |
        """))

        results = detector.detect_phantom_entries(str(tmp_project))
        phantoms = [
            r
            for r in results
            if r.type == "phantom_entry" and "real-skill" in r.component
        ]
        assert len(phantoms) == 0

    def test_detects_dead_config_flag(self, detector, tmp_project):
        """A config key not referenced by any code should be flagged."""
        (tmp_project / "cognitive-os.yaml").write_text(textwrap.dedent("""\
            project:
              zzz_unused_flag_xyz: true
        """))
        # No code references zzz_unused_flag_xyz
        (tmp_project / "lib" / "helper.py").write_text("x = 1\n")

        results = detector.detect_phantom_entries(str(tmp_project))
        config_phantoms = [
            r for r in results if "zzz_unused_flag_xyz" in r.component
        ]
        assert len(config_phantoms) >= 1


# ---------------------------------------------------------------------------
# Structural Tests Detection
# ---------------------------------------------------------------------------
class TestStructuralTests:
    def test_detects_existence_only_test(self, detector, tmp_project):
        """A test with only path.exists() assertions should be flagged."""
        test_dir = tmp_project / "tests"
        (test_dir / "test_existence.py").write_text(textwrap.dedent("""\
            import os
            from pathlib import Path

            def test_file_exists():
                p = Path("something.py")
                assert p.exists()

            def test_another_exists():
                assert os.path.isfile("other.py")
        """))

        results = detector.detect_structural_tests(str(tmp_project))
        structural = [r for r in results if r.type == "structural_test"]
        assert len(structural) >= 1
        assert any("test_existence.py" in r.component for r in structural)

    def test_behavioral_test_not_flagged(self, detector, tmp_project):
        """A test with actual behavioral assertions should NOT be flagged."""
        test_dir = tmp_project / "tests"
        (test_dir / "test_behavior.py").write_text(textwrap.dedent("""\
            def test_addition():
                assert 1 + 1 == 2

            def test_string():
                assert "hello".upper() == "HELLO"
        """))

        results = detector.detect_structural_tests(str(tmp_project))
        structural = [
            r for r in results if "test_behavior.py" in r.component
        ]
        assert len(structural) == 0

    def test_mixed_test_not_flagged(self, detector, tmp_project):
        """A test with both structural and behavioral assertions is NOT flagged."""
        test_dir = tmp_project / "tests"
        (test_dir / "test_mixed.py").write_text(textwrap.dedent("""\
            from pathlib import Path

            def test_file_and_content():
                assert Path("x.py").exists()
                result = 2 + 2
                assert result == 4
        """))

        results = detector.detect_structural_tests(str(tmp_project))
        structural = [r for r in results if "test_mixed.py" in r.component]
        assert len(structural) == 0


# ---------------------------------------------------------------------------
# Run All & Report
# ---------------------------------------------------------------------------
class TestRunAll:
    def test_run_all_combines_results(self, detector, tmp_project):
        """run_all should return results from all detectors."""
        # Set up a phantom entry
        catalog = tmp_project / "skills" / "CATALOG.md"
        catalog.write_text(textwrap.dedent("""\
            # Catalog

            | Skill | Description | Invoke | Audience |
            |-------|-------------|--------|----------|
            | phantom | Nope | `/phantom` | os |
        """))

        # Set up a broken chain
        (tmp_project / "lib" / "broken.py").write_text(
            "from lib.does_not_exist import foo\n"
        )

        results = detector.run_all(str(tmp_project))
        types_found = {r.type for r in results}
        assert "phantom_entry" in types_found
        assert "broken_chain" in types_found

    def test_run_type_filters(self, detector, tmp_project):
        """run_type should only return results for the specified type."""
        catalog = tmp_project / "skills" / "CATALOG.md"
        catalog.write_text(textwrap.dedent("""\
            # Catalog

            | Skill | Description | Invoke | Audience |
            |-------|-------------|--------|----------|
            | phantom | Nope | `/phantom` | os |
        """))

        results = detector.run_type(str(tmp_project), "phantoms")
        assert all(r.type == "phantom_entry" for r in results)

    def test_run_type_invalid_raises(self, detector, tmp_project):
        """run_type with unknown type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown detection type"):
            detector.run_type(str(tmp_project), "nonexistent")

    def test_format_report_empty(self, detector):
        """format_report with no issues returns clean message."""
        report = detector.format_report([])
        assert "No systemic issues" in report

    def test_format_report_groups_by_severity(self, detector):
        """format_report should group results by severity."""
        patterns = [
            DetectedPattern(
                type="broken_chain",
                severity="critical",
                component="lib/bad.py",
                description="Broken import",
                evidence="Not found",
                suggestion="Fix it",
            ),
            DetectedPattern(
                type="dead_metadata",
                severity="warning",
                component="frontmatter.x",
                description="Unused field",
                evidence="No readers",
                suggestion="Remove it",
            ),
        ]
        report = detector.format_report(patterns)
        assert "CRITICAL" in report
        assert "WARNING" in report
        # CRITICAL should appear before WARNING
        assert report.index("CRITICAL") < report.index("WARNING")


# ---------------------------------------------------------------------------
# _parse_frontmatter_keys — real-file integration (B1 parser audit fix)
# ---------------------------------------------------------------------------


class TestParseFrontmatterKeysRealFiles:
    """Integration tests that exercise _parse_frontmatter_keys against actual
    SKILL.md files in the repo, including those with HTML-comment prefixes."""

    def test_plain_frontmatter_returns_keys(self, tmp_path):
        """Standard ``---`` delimited frontmatter returns the expected keys."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: my-skill\ndescription: Does stuff\nversion: 1.0\n---\n# Body\n")
        keys = PatternDetector._parse_frontmatter_keys(skill_md.read_text())
        assert "name" in keys
        assert "description" in keys
        assert "version" in keys

    def test_html_comment_prefix_frontmatter_returns_keys(self, tmp_path):
        """SKILL.md with ``<!-- SCOPE: both -->`` before the opening fence is parsed correctly."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("<!-- SCOPE: both -->\n---\nname: add-hook\ndescription: Step-by-step guide\nversion: 0.1.0\n---\n")
        keys = PatternDetector._parse_frontmatter_keys(skill_md.read_text())
        assert "name" in keys
        assert "description" in keys
        assert "version" in keys

    def test_no_frontmatter_returns_empty(self, tmp_path):
        """Files without YAML frontmatter return an empty list."""
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("# Just a heading\nSome body text.\n")
        keys = PatternDetector._parse_frontmatter_keys(skill_md.read_text())
        assert keys == []

    def test_real_skill_with_html_prefix(self):
        """Smoke test: parse a real SKILL.md that has an HTML comment prefix."""
        import pathlib
        repo_root = pathlib.Path(__file__).parent.parent.parent
        skill_md = repo_root / "skills" / "add-hook" / "SKILL.md"
        if not skill_md.exists():
            pytest.skip("skills/add-hook/SKILL.md not present")
        keys = PatternDetector._parse_frontmatter_keys(skill_md.read_text())
        assert "name" in keys, f"Expected 'name' key, got: {keys}"
        assert "description" in keys, f"Expected 'description' key, got: {keys}"
