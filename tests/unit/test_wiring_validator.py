"""Unit tests for lib/wiring_validator.py using a mocked project tree."""
import textwrap
from pathlib import Path

import pytest

from lib.wiring_validator import WiringValidator


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_project(tmp_path: Path) -> Path:
    """Create a minimal mock project tree."""
    # hooks/
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    (hooks / "fully-wired.sh").write_text("#!/usr/bin/env bash\necho ok")
    (hooks / "file-only.sh").write_text("#!/usr/bin/env bash\necho ok")
    (hooks / "missing-efficiency.sh").write_text("#!/usr/bin/env bash\necho ok")
    (hooks / "_lib-helper.sh").write_text("#!/usr/bin/env bash\n# internal")

    # lib/
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "imported_lib.py").write_text("def foo(): pass")
    (lib / "orphan_lib.py").write_text("def bar(): pass")
    (lib / "no_tests_lib.py").write_text("def baz(): pass")

    # tests/unit/
    tests = tmp_path / "tests" / "unit"
    tests.mkdir(parents=True)
    (tests / "test_imported_lib.py").write_text("from lib.imported_lib import foo")
    # NOTE: no_tests_lib intentionally has NO test file

    # A consumer that imports imported_lib AND no_tests_lib
    (lib / "consumer.py").write_text(
        "from lib.imported_lib import foo\nfrom lib.no_tests_lib import baz"
    )

    # rules/
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "RULES-COMPACT.md").write_text(
        textwrap.dedent("""\
            # Rules
            See `in-compact.md` for details [`in-compact`].
        """)
    )
    (rules / "in-compact.md").write_text("# In compact")
    (rules / "excluded-rule.md").write_text("# Excluded rule")
    (rules / "nowhere-rule.md").write_text("# Nowhere")

    # .claude/rules/ symlink for in-compact.md
    claude_rules = tmp_path / ".claude" / "rules"
    claude_rules.mkdir(parents=True)
    (claude_rules / "in-compact.md").symlink_to(rules / "in-compact.md")

    # hooks/self-install.sh with EXCLUDED_RULES
    (hooks / "self-install.sh").write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        EXCLUDED_RULES=(
          "excluded-rule.md"  # excluded by design
        )
    """))

    # scripts/ — security + efficiency profiles
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "set-security-profile.sh").write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        # Register fully-wired.sh and missing-efficiency.sh in security profiles
        hook_group() { echo "$@"; }
        # standard profile
        fully-wired.sh
        missing-efficiency.sh
    """))
    (scripts / "apply-efficiency-profile.sh").write_text(textwrap.dedent("""\
        #!/usr/bin/env bash
        # Efficiency profile — only the wired hook is listed here
        hook_group() { echo "$@"; }
        # standard profile
        fully-wired.sh
    """))

    # .claude/settings.json — fully-wired.sh active
    claude = tmp_path / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / "settings.json").write_text(
        '{"hooks": {"PostToolUse": [{"command": "hooks/fully-wired.sh"}]}}'
    )

    return tmp_path


# ── Hook tests ────────────────────────────────────────────────────────────────

class TestHookValidation:
    def test_hook_fully_wired(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_hook("fully-wired.sh")
        assert result["file_exists"] is True
        assert result["in_security_profile"] is True
        assert result["in_efficiency_profile"] is True
        assert result["in_settings_json"] is True
        assert result["wiring_score"] == 1.0
        assert result["issues"] == []

    def test_hook_file_only(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_hook("file-only.sh")
        assert result["file_exists"] is True
        assert result["in_security_profile"] is False
        assert result["in_efficiency_profile"] is False
        assert result["in_settings_json"] is False
        assert result["wiring_score"] == pytest.approx(0.25)
        assert len(result["issues"]) >= 2

    def test_hook_missing_efficiency(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_hook("missing-efficiency.sh")
        assert result["in_security_profile"] is True
        assert result["in_efficiency_profile"] is False
        # file=1, security=1, efficiency=0, settings=0 → 0.5
        assert result["wiring_score"] == pytest.approx(0.5)

    def test_hook_internal_skipped(self, mock_project: Path) -> None:
        """_lib hooks are skipped from validate_all_hooks but can still be validated."""
        v = WiringValidator(str(mock_project))
        all_names = [r["name"] for r in v.validate_all_hooks()]
        assert "_lib-helper.sh" not in all_names

    def test_validate_all_hooks_sorted(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        results = v.validate_all_hooks()
        scores = [r["wiring_score"] for r in results]
        assert scores == sorted(scores), "Results must be sorted ascending by wiring_score"


# ── Lib tests ─────────────────────────────────────────────────────────────────

class TestLibValidation:
    def test_lib_imported(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_lib("imported_lib.py")
        assert result["file_exists"] is True
        assert len(result["imported_by"]) >= 1
        assert result["has_tests"] is True
        assert result["wiring_score"] == pytest.approx(1.0)

    def test_lib_no_importers(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_lib("orphan_lib.py")
        assert result["imported_by"] == []
        # file=1, importers=0, tests=0 → 1/3
        assert result["wiring_score"] == pytest.approx(1 / 3)
        assert any("import" in i for i in result["issues"])

    def test_lib_no_tests(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_lib("no_tests_lib.py")
        assert result["file_exists"] is True
        assert len(result["imported_by"]) >= 1  # consumer.py imports it
        assert result["has_tests"] is False
        # file=1, importers=1, tests=0 → 2/3
        assert result["wiring_score"] == pytest.approx(2 / 3)


# ── Rule tests ────────────────────────────────────────────────────────────────

class TestRuleValidation:
    def test_rule_in_compact(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_rule("in-compact.md")
        assert result["in_rules_compact"] is True
        assert result["in_claude_rules"] is True
        assert result["wiring_score"] == pytest.approx(1.0)

    def test_rule_excluded(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_rule("excluded-rule.md")
        assert result["in_excluded_rules"] is True
        assert result["wiring_score"] == pytest.approx(1.0)
        assert result["issues"] == []

    def test_rule_nowhere(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.validate_rule("nowhere-rule.md")
        assert result["in_rules_compact"] is False
        assert result["in_excluded_rules"] is False
        assert result["wiring_score"] < 1.0
        assert len(result["issues"]) >= 1


# ── Aggregate tests ───────────────────────────────────────────────────────────

class TestAggregateValidation:
    def test_unwired_components_structure(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        result = v.get_unwired_components()
        assert "hooks" in result
        assert "libs" in result
        assert "rules" in result
        assert "total_unwired" in result
        assert isinstance(result["total_unwired"], int)
        assert result["total_unwired"] > 0

    def test_format_report_readable(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        report = v.format_wiring_report()
        assert "WIRING REPORT" in report
        assert "HOOKS:" in report
        assert "LIBS:" in report
        assert "RULES:" in report

    def test_format_fix_commands(self, mock_project: Path) -> None:
        v = WiringValidator(str(mock_project))
        fixes = v.format_fix_commands()
        assert "FIX COMMANDS" in fixes
        # At least one fix should mention set-security-profile or apply-efficiency
        assert "set-security-profile" in fixes or "apply-efficiency" in fixes
