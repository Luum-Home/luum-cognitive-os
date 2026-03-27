"""
Architecture Principles Tests

Validates the 5-layer dependency model:
  Layer 1: Rules (rules/*.md) - no dependencies
  Layer 2: Skills (skills/*/SKILL.md) - may reference rules by name
  Layer 3: Hooks (hooks/*.sh) - may source hooks/_lib/, read rules/config
  Layer 4: Libs (lib/*.py) - may import stdlib + approved packages
  Layer 5: Externals (docker-compose, APIs) - accessed only through libs

Dependencies ONLY point inward (toward Layer 1).
"""

import re
from pathlib import Path

import yaml
import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    """Read file content, returning empty string on error."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return ""


def _rule_files() -> list[Path]:
    """All markdown files in rules/."""
    rules_dir = PROJECT_ROOT / "rules"
    return sorted(rules_dir.glob("*.md")) if rules_dir.is_dir() else []


def _skill_files() -> list[Path]:
    """All SKILL.md files."""
    skills_dir = PROJECT_ROOT / "skills"
    return sorted(skills_dir.rglob("SKILL.md")) if skills_dir.is_dir() else []


def _hook_files() -> list[Path]:
    """All .sh files in hooks/ (excluding _lib/)."""
    hooks_dir = PROJECT_ROOT / "hooks"
    if not hooks_dir.is_dir():
        return []
    return sorted(
        p for p in hooks_dir.glob("*.sh")
        if not p.name.startswith("_")
    )


def _lib_files() -> list[Path]:
    """All .py files in lib/ (excluding __init__.py)."""
    lib_dir = PROJECT_ROOT / "lib"
    if not lib_dir.is_dir():
        return []
    return sorted(
        p for p in lib_dir.glob("*.py")
        if p.name != "__init__.py"
    )


# ---------------------------------------------------------------------------
# Test 1: Rules do not import Python modules
# ---------------------------------------------------------------------------

class TestLayerDependencies:
    """Verify the 5-layer dependency rule is not violated."""

    def test_rules_do_not_import_python(self):
        """Layer 1 (rules) must not contain Python import statements."""
        python_import_re = re.compile(
            r"^(import |from \S+ import )",
            re.MULTILINE,
        )
        violations = []
        for rule_file in _rule_files():
            content = _read_text(rule_file)
            # Skip fenced code blocks (```...```) which may contain example imports
            # Remove code blocks before checking
            no_code = re.sub(r"```[\s\S]*?```", "", content)
            if python_import_re.search(no_code):
                violations.append(rule_file.name)

        assert not violations, (
            f"Rules must not contain Python imports (outside code blocks): {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 2: Rules do not reference hook filenames
    # ---------------------------------------------------------------------------

    def test_rules_do_not_reference_hook_filenames_as_dependencies(self):
        """Layer 1 (rules) should not depend on specific hook filenames.

        Rules may MENTION hooks for documentation purposes (e.g., 'the
        trust-score-validator.sh hook logs scores'), but the rule's behavioral
        constraint must not DEPEND on a specific hook existing.

        We check that rules do not contain 'source hooks/' or 'bash hooks/'
        patterns which would indicate a hard dependency.
        """
        # Rules that legitimately reference hook filenames as documentation
        # (describing which hooks enforce the rule, not depending on them).
        EXCEPTIONS = {
            "agent-security.md",  # documents which hooks enforce security policy
        }

        hard_dep_patterns = [
            re.compile(r"source\s+.*hooks/", re.IGNORECASE),
            re.compile(r"bash\s+.*hooks/", re.IGNORECASE),
            re.compile(r"\./hooks/\S+\.sh", re.IGNORECASE),
        ]
        violations = []
        for rule_file in _rule_files():
            if rule_file.name in EXCEPTIONS:
                continue
            content = _read_text(rule_file)
            no_code = re.sub(r"```[\s\S]*?```", "", content)
            for pattern in hard_dep_patterns:
                if pattern.search(no_code):
                    violations.append(rule_file.name)
                    break

        assert not violations, (
            f"Rules must not have hard dependencies on hook scripts: {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 3: Skills do not contain implementation code blocks
    # ---------------------------------------------------------------------------

    def test_skills_do_not_contain_implementation_code(self):
        """Layer 2 (skills) should be LLM instructions, not executable code.

        Skills may contain ILLUSTRATIVE code blocks (examples for the agent),
        but should not contain large executable scripts that ARE the
        implementation. We flag skills with code blocks exceeding 60 lines
        as likely antipatterns.
        """
        code_block_re = re.compile(r"```(?:python|bash|sh)\n([\s\S]*?)```")
        violations = []
        for skill_file in _skill_files():
            content = _read_text(skill_file)
            for match in code_block_re.finditer(content):
                block = match.group(1)
                line_count = block.count("\n") + 1
                if line_count > 60:
                    rel = skill_file.relative_to(PROJECT_ROOT)
                    violations.append(f"{rel} ({line_count} lines)")

        assert not violations, (
            f"Skills should not contain large implementation code blocks "
            f"(>50 lines). These likely belong in lib/: {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 4: Hooks source only from hooks/_lib/
    # ---------------------------------------------------------------------------

    def test_hooks_source_only_from_lib(self):
        """Layer 3 (hooks) should only source shared code from hooks/_lib/.

        Hooks must not source scripts from lib/, rules/, or skills/.
        """
        # Match 'source' or '.' (dot-source) followed by a path
        source_re = re.compile(
            r'(?:^|\s)(?:source|\.)\s+"?([^";\s]+)"?',
            re.MULTILINE,
        )
        violations = []
        for hook_file in _hook_files():
            content = _read_text(hook_file)
            for match in source_re.finditer(content):
                sourced = match.group(1)
                # Allow sourcing from hooks/_lib/ or relative _lib/
                if "_lib/" in sourced or "common.sh" in sourced:
                    continue
                # Allow sourcing from $HOOK_DIR/_lib patterns
                if "$" in sourced and "_lib" in sourced:
                    continue
                # Flag sourcing from other directories
                if any(d in sourced for d in ["lib/", "rules/", "skills/"]):
                    violations.append(f"{hook_file.name} sources {sourced}")

        assert not violations, (
            f"Hooks should only source from hooks/_lib/: {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 5: Libs do not read from rules/ directory
    # ---------------------------------------------------------------------------

    def test_libs_do_not_read_rules(self):
        """Layer 4 (libs) must not parse rules/*.md files directly.

        Libs should receive parameters via config or function arguments,
        not by reading markdown rule files.
        """
        # Libs whose purpose is to scan the entire project structure
        # (including rules/) are exempt from this constraint.
        EXCEPTIONS = {
            "system_graph.py",  # scans all project layers to build dependency graph
        }

        rules_read_re = re.compile(
            r"""(?:open|read_text|Path)\s*\(.*['"](\.\.\/)?rules\/""",
            re.MULTILINE,
        )
        # Also check for os.path patterns
        ospath_re = re.compile(
            r"""os\.path\.join\s*\(.*['"]rules['"]""",
            re.MULTILINE,
        )
        violations = []
        for lib_file in _lib_files():
            if lib_file.name in EXCEPTIONS:
                continue
            content = _read_text(lib_file)
            if rules_read_re.search(content) or ospath_re.search(content):
                violations.append(lib_file.name)

        assert not violations, (
            f"Libs must not read rules/*.md directly. "
            f"Use config or parameters instead: {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 6: Each layer has appropriate test coverage categories
    # ---------------------------------------------------------------------------

    def test_test_categories_exist(self):
        """Verify test directories exist for different layer categories."""
        tests_dir = PROJECT_ROOT / "tests"
        expected = {
            "behavior": "Rules, Skills, Hooks (behavior tests)",
            "unit": "Libs (unit tests)",
        }
        missing = []
        for dirname, purpose in expected.items():
            if not (tests_dir / dirname).is_dir():
                missing.append(f"{dirname}/ for {purpose}")

        assert not missing, (
            f"Missing test directories: {missing}"
        )

    # ---------------------------------------------------------------------------
    # Test 7: cognitive-os.yaml is valid YAML
    # ---------------------------------------------------------------------------

    def test_config_is_valid_yaml(self):
        """cognitive-os.yaml must be parseable YAML."""
        config_path = PROJECT_ROOT / "cognitive-os.yaml"
        if not config_path.exists():
            pytest.skip("cognitive-os.yaml not found")

        content = config_path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            pytest.fail(f"cognitive-os.yaml is not valid YAML: {exc}")

        assert isinstance(data, dict), "cognitive-os.yaml should parse to a dict"

    # ---------------------------------------------------------------------------
    # Test 8: No circular dependencies between hook and lib
    # ---------------------------------------------------------------------------

    def test_no_hooks_imported_by_libs(self):
        """Libs must not import or execute hook scripts.

        This would create a circular dependency: hooks call libs,
        but libs must not call hooks.
        """
        hook_call_re = re.compile(
            r"""(?:subprocess|os\.system|Popen)\s*\(.*hooks/""",
            re.MULTILINE,
        )
        violations = []
        for lib_file in _lib_files():
            content = _read_text(lib_file)
            if hook_call_re.search(content):
                violations.append(lib_file.name)

        assert not violations, (
            f"Libs must not call hook scripts (circular dependency): {violations}"
        )

    # ---------------------------------------------------------------------------
    # Test 9: Dependency direction check - hooks reference rules, not reverse
    # ---------------------------------------------------------------------------

    def test_dependency_direction_hooks_reference_rules(self):
        """Sample hooks should reference rules (inward), and rules should
        not reference hooks as dependencies (outward).

        We verify that at least some hooks contain references to rules/
        (correct direction), confirming the dependency flows inward.
        """
        hooks = _hook_files()
        if len(hooks) < 5:
            pytest.skip("Not enough hooks to sample")

        # Sample up to 10 hooks
        sample = hooks[:10]
        hooks_referencing_rules = 0
        for hook_file in sample:
            content = _read_text(hook_file)
            if "rules/" in content or "cognitive-os.yaml" in content:
                hooks_referencing_rules += 1

        # At least some hooks should reference rules or config (inward deps)
        assert hooks_referencing_rules >= 1, (
            f"Expected at least 1 of {len(sample)} sampled hooks to reference "
            f"rules/ or cognitive-os.yaml (inward dependency), found 0"
        )

    # ---------------------------------------------------------------------------
    # Test 10: Layer size proportions are reasonable
    # ---------------------------------------------------------------------------

    def test_layer_size_proportions(self):
        """Layer sizes should follow a reasonable distribution.

        Rules (Layer 1) should be the smallest set of files.
        Skills + Hooks + Libs (Layers 2-4) should be larger.
        This ensures rules stay focused on intent, not implementation.
        """
        rules_count = len(_rule_files())
        skills_count = len(_skill_files())
        hooks_count = len(_hook_files())
        libs_count = len(_lib_files())

        # Basic sanity: we have components in each layer
        assert rules_count > 0, "No rule files found"
        assert skills_count > 0, "No skill files found"
        assert hooks_count > 0, "No hook files found"
        assert libs_count > 0, "No lib files found"

        # Rules should not vastly outnumber everything else combined
        # (would indicate rules are doing too much work)
        implementation_count = skills_count + hooks_count + libs_count
        assert implementation_count > rules_count, (
            f"Implementation layers ({implementation_count} files) should "
            f"outnumber rules ({rules_count} files). "
            f"If rules dominate, they may be doing implementation work."
        )
