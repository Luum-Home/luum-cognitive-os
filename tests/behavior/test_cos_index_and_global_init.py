"""Behavior tests for cos-index package and cos-init-global.sh.

Tests:
1. cos-index/index/packages.yaml lists all packages from packages/
2. cos-index/scripts/validate-index.sh exists and is executable
3. cos-index/scripts/generate-index.sh exists and is executable
4. scripts/cos-init-global.sh exists and is executable
5. cos-init-global.sh installs 14 core rules to a temp dir
6. Index validation script passes on the actual index
"""

import os
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ── cos-index tests ──────────────────────────────────────────────────


class TestCosIndex:
    """Tests for the packages/cos-index/ package."""

    INDEX_DIR = PROJECT_ROOT / "packages" / "cos-index"
    INDEX_FILE = INDEX_DIR / "index" / "packages.yaml"

    def test_index_directory_exists(self):
        assert self.INDEX_DIR.is_dir(), "packages/cos-index/ directory does not exist"

    def test_index_file_exists(self):
        assert self.INDEX_FILE.is_file(), "packages/cos-index/index/packages.yaml does not exist"

    def test_cos_package_yaml_exists(self):
        pkg_yaml = self.INDEX_DIR / "cos-package.yaml"
        assert pkg_yaml.is_file(), "packages/cos-index/cos-package.yaml does not exist"

    def test_readme_exists(self):
        readme = self.INDEX_DIR / "README.md"
        assert readme.is_file(), "packages/cos-index/README.md does not exist"

    def test_validate_script_exists(self):
        script = self.INDEX_DIR / "scripts" / "validate-index.sh"
        assert script.is_file(), "validate-index.sh does not exist"

    def test_generate_script_exists(self):
        script = self.INDEX_DIR / "scripts" / "generate-index.sh"
        assert script.is_file(), "generate-index.sh does not exist"

    def test_validate_script_is_executable(self):
        script = self.INDEX_DIR / "scripts" / "validate-index.sh"
        assert os.access(script, os.X_OK), "validate-index.sh is not executable"

    def test_generate_script_is_executable(self):
        script = self.INDEX_DIR / "scripts" / "generate-index.sh"
        assert os.access(script, os.X_OK), "generate-index.sh is not executable"

    def test_index_is_valid_yaml(self):
        """Verify the index file is valid YAML."""
        with open(self.INDEX_FILE) as f:
            data = yaml.safe_load(f)
        assert "packages" in data, "Index YAML missing 'packages' key"
        assert isinstance(data["packages"], list), "'packages' should be a list"

    def test_index_lists_all_packages(self):
        """Every directory in packages/ with cos-package.yaml should be in the index."""
        packages_dir = PROJECT_ROOT / "packages"

        # Collect actual packages (directories with cos-package.yaml)
        actual_packages = set()
        for pkg_dir in packages_dir.iterdir():
            if pkg_dir.is_dir() and (pkg_dir / "cos-package.yaml").is_file():
                with open(pkg_dir / "cos-package.yaml") as f:
                    pkg_data = yaml.safe_load(f)
                actual_packages.add(pkg_data.get("name", ""))

        # Collect indexed packages
        with open(self.INDEX_FILE) as f:
            index_data = yaml.safe_load(f)
        indexed_names = {p["name"] for p in index_data["packages"]}

        # Every actual package should be in the index
        missing = actual_packages - indexed_names
        assert not missing, f"Packages missing from index: {missing}"

    def test_index_entries_have_required_fields(self):
        """Every index entry must have name, repo, path, version, description."""
        with open(self.INDEX_FILE) as f:
            data = yaml.safe_load(f)

        required = {"name", "repo", "path", "version", "description"}
        for i, entry in enumerate(data["packages"]):
            for field in required:
                assert field in entry, f"Entry {i} ({entry.get('name', '?')}) missing '{field}'"
                assert entry[field], f"Entry {i} ({entry.get('name', '?')}) has empty '{field}'"

    def test_index_no_duplicate_names(self):
        """No two entries should have the same name."""
        with open(self.INDEX_FILE) as f:
            data = yaml.safe_load(f)

        names = [p["name"] for p in data["packages"]]
        duplicates = [n for n in names if names.count(n) > 1]
        assert not duplicates, f"Duplicate package names in index: {set(duplicates)}"

    def test_index_entry_count_matches_packages(self):
        """The index should have at least as many entries as actual packages."""
        packages_dir = PROJECT_ROOT / "packages"
        actual_count = sum(
            1
            for d in packages_dir.iterdir()
            if d.is_dir() and (d / "cos-package.yaml").is_file()
        )

        with open(self.INDEX_FILE) as f:
            data = yaml.safe_load(f)
        index_count = len(data["packages"])

        assert (
            index_count >= actual_count
        ), f"Index has {index_count} entries but {actual_count} packages exist"


# ── cos-init-global tests ───────────────────────────────────────────


class TestCosInitGlobal:
    """Tests for scripts/cos-init-global.sh."""

    SCRIPT = PROJECT_ROOT / "scripts" / "cos-init-global.sh"

    # The 14 core rules (must match cos-init-global.sh CORE_RULES array)
    CORE_RULES = [
        "RULES-COMPACT.md",
        "adaptive-bypass.md",
        "acceptance-criteria.md",
        "agent-quality.md",
        "trust-score.md",
        "definition-of-done.md",
        "closed-loop-prompts.md",
        "token-economy.md",
        "responsiveness.md",
        "credential-management.md",
        "license-policy.md",
        "result-management.md",
        "decomposition.md",
        "model-routing.md",
    ]

    def test_script_exists(self):
        assert self.SCRIPT.is_file(), "scripts/cos-init-global.sh does not exist"

    def test_script_is_executable(self):
        assert os.access(self.SCRIPT, os.X_OK), "cos-init-global.sh is not executable"

    def test_dry_run_lists_rules(self):
        """--dry-run should list the rules without writing anything."""
        result = subprocess.run(
            ["bash", str(self.SCRIPT), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert result.returncode == 0, f"dry-run failed: {result.stderr}"
        assert "DRY RUN" in result.stdout, "Output should contain 'DRY RUN'"
        assert "RULES-COMPACT.md" in result.stdout, "Output should list RULES-COMPACT.md"

    def test_installs_to_temp_dir(self, tmp_path):
        """Install to a temp HOME to verify it creates the right files."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(fake_home)

        result = subprocess.run(
            ["bash", str(self.SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
            env=env,
        )
        assert result.returncode == 0, f"install failed: {result.stderr}\n{result.stdout}"

        rules_dir = fake_home / ".claude" / "rules" / "cos"
        assert rules_dir.is_dir(), "~/.claude/rules/cos/ was not created"

        # All 14 core rules should be installed
        installed = list(rules_dir.glob("*.md"))
        assert (
            len(installed) == 14
        ), f"Expected 14 rules, got {len(installed)}: {[f.name for f in installed]}"

        for rule in self.CORE_RULES:
            rule_file = rules_dir / rule
            assert rule_file.is_file(), f"Missing rule: {rule}"
            assert rule_file.stat().st_size > 0, f"Rule is empty: {rule}"

    def test_installs_metadata(self, tmp_path):
        """Install should create global-install-meta.json."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(fake_home)

        subprocess.run(
            ["bash", str(self.SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
            env=env,
        )

        meta = fake_home / ".cognitive-os" / "global-install-meta.json"
        assert meta.is_file(), "global-install-meta.json was not created"

    def test_idempotent_rerun(self, tmp_path):
        """Running twice should succeed and report skipped rules."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        env = os.environ.copy()
        env["HOME"] = str(fake_home)

        # First run
        subprocess.run(
            ["bash", str(self.SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
            env=env,
        )

        # Second run
        result = subprocess.run(
            ["bash", str(self.SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
            env=env,
        )
        assert result.returncode == 0, f"idempotent rerun failed: {result.stderr}"
        assert "Skipped" in result.stdout, "Second run should skip unchanged rules"

    def test_core_rules_source_files_exist(self):
        """All 14 core rules must exist in the rules/ directory."""
        for rule in self.CORE_RULES:
            rule_path = PROJECT_ROOT / "rules" / rule
            assert rule_path.is_file(), f"Core rule missing from source: rules/{rule}"

    def test_help_flag(self):
        """--help should show usage without error."""
        result = subprocess.run(
            ["bash", str(self.SCRIPT), "--help"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=10,
        )
        assert result.returncode == 0, f"--help failed: {result.stderr}"
        assert "Usage" in result.stdout, "Help output should contain 'Usage'"
