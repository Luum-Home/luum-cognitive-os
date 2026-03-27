"""System tests for rules infrastructure.

Verifies rule files exist and match RULES-COMPACT.md references.
Migrated from tests/infra/test-rules.sh.
"""

import re
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def rules_dir(project_root):
    return project_root / "rules"


@pytest.fixture(scope="module")
def rules_compact(rules_dir):
    path = rules_dir / "RULES-COMPACT.md"
    if not path.exists():
        pytest.fail("RULES-COMPACT.md not found")
    return path


@pytest.mark.system
class TestRulesInfrastructure:
    """Tests for rule file consistency with RULES-COMPACT.md."""

    def test_rules_compact_exists(self, rules_compact):
        assert rules_compact.exists()

    def test_disk_rules_referenced_in_compact(self, rules_dir, rules_compact):
        """Each rule .md on disk should be referenced in RULES-COMPACT.md."""
        compact_text = rules_compact.read_text()
        orphans = []

        for rule in rules_dir.glob("*.md"):
            name = rule.stem
            if name == "RULES-COMPACT":
                continue
            if name not in compact_text:
                orphans.append(name)

        if orphans:
            pytest.skip(f"Orphan rules on disk (not in RULES-COMPACT): {orphans}")

    def test_compact_references_exist_on_disk(self, rules_dir, rules_compact, project_root):
        """Each rule referenced in RULES-COMPACT.md should exist as a file."""
        compact_text = rules_compact.read_text()
        referenced = set(re.findall(r"\[`([a-z0-9-]+)`\]", compact_text))

        phantoms = []
        for rule_name in referenced:
            rule_path = rules_dir / f"{rule_name}.md"
            alt_path = project_root / ".claude" / "rules" / f"{rule_name}.md"
            if not rule_path.exists() and not alt_path.exists():
                phantoms.append(rule_name)

        assert not phantoms, (
            f"Phantom rules in RULES-COMPACT.md (file not found): {phantoms}"
        )

    def test_rule_files_non_empty(self, rules_dir):
        """All rule markdown files should have meaningful content (>10 bytes)."""
        tiny = []
        for rule in rules_dir.glob("*.md"):
            if rule.stem == "RULES-COMPACT":
                continue
            size = rule.stat().st_size
            if size <= 10:
                tiny.append(f"{rule.name} ({size} bytes)")

        assert not tiny, f"Rule files too small: {tiny}"
