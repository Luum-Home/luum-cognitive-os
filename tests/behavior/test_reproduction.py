"""Tests for the Reproduction system (memory inheritance during project spawning)."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COS_SCRIPT = PROJECT_ROOT / "bin" / "cognitive-os.sh"


def run_cos_init(target_dir: Path, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run `cos init` on a target directory."""
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        ["bash", str(COS_SCRIPT), "init", str(target_dir)],
        capture_output=True,
        text=True,
        env=run_env,
        timeout=30,
    )


class TestSeedMemoryCreation:
    """cos init should create seed-memory.md when a stack is detected."""

    def test_cos_init_creates_seed_memory_for_node_project(self, tmp_path: Path):
        """Projects with package.json should get a seed-memory.md with node keywords."""
        target = tmp_path / "my-node-app"
        target.mkdir()
        (target / "package.json").write_text('{"name": "test"}')

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists(), "seed-memory.md should be created for node projects"
        content = seed.read_text()
        assert "node" in content
        assert "typescript" in content
        assert "Inherited from Parent Organism" in content

    def test_cos_init_creates_seed_memory_for_go_project(self, tmp_path: Path):
        """Projects with go.mod should get go/golang keywords."""
        target = tmp_path / "my-go-app"
        target.mkdir()
        (target / "go.mod").write_text("module example.com/test\n\ngo 1.22\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists(), "seed-memory.md should be created for go projects"
        content = seed.read_text()
        assert "go" in content
        assert "golang" in content

    def test_cos_init_creates_seed_memory_for_python_project(self, tmp_path: Path):
        """Projects with requirements.txt should get python keywords."""
        target = tmp_path / "my-python-app"
        target.mkdir()
        (target / "requirements.txt").write_text("flask==3.0\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "python" in content

    def test_cos_init_creates_seed_memory_for_pyproject_toml(self, tmp_path: Path):
        """Projects with pyproject.toml should get python keywords."""
        target = tmp_path / "my-python-app"
        target.mkdir()
        (target / "pyproject.toml").write_text('[project]\nname = "test"\n')

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "python" in content

    def test_cos_init_creates_seed_memory_for_rust_project(self, tmp_path: Path):
        """Projects with Cargo.toml should get rust keywords."""
        target = tmp_path / "my-rust-app"
        target.mkdir()
        (target / "Cargo.toml").write_text('[package]\nname = "test"\n')

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "rust" in content

    def test_cos_init_creates_seed_memory_for_java_project(self, tmp_path: Path):
        """Projects with pom.xml should get java/spring keywords."""
        target = tmp_path / "my-java-app"
        target.mkdir()
        (target / "pom.xml").write_text("<project></project>")

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "java" in content
        assert "spring" in content

    def test_cos_init_creates_seed_memory_for_docker_project(self, tmp_path: Path):
        """Projects with docker-compose.yml should get docker/infrastructure keywords."""
        target = tmp_path / "my-docker-app"
        target.mkdir()
        (target / "docker-compose.yml").write_text("version: '3'\nservices: {}\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "docker" in content
        assert "infrastructure" in content

    def test_cos_init_combines_multiple_stacks(self, tmp_path: Path):
        """Projects with multiple stack files should get combined keywords."""
        target = tmp_path / "my-fullstack-app"
        target.mkdir()
        (target / "package.json").write_text('{"name": "test"}')
        (target / "docker-compose.yml").write_text("version: '3'\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert seed.exists()
        content = seed.read_text()
        assert "node" in content
        assert "docker" in content

    def test_cos_init_no_seed_memory_for_empty_project(self, tmp_path: Path):
        """Projects with no recognized stack files should not get seed-memory.md."""
        target = tmp_path / "empty-project"
        target.mkdir()

        result = run_cos_init(target)

        assert result.returncode == 0
        seed = target / ".cognitive-os" / "seed-memory.md"
        assert not seed.exists(), "No seed-memory.md for projects without recognized stack"
        assert "Starting fresh" in result.stdout


class TestSeedMemoryContent:
    """Verify the structure and content of seed-memory.md."""

    def test_seed_memory_has_header(self, tmp_path: Path):
        """seed-memory.md should have the standard header."""
        target = tmp_path / "test-app"
        target.mkdir()
        (target / "package.json").write_text('{}')

        run_cos_init(target)

        seed = target / ".cognitive-os" / "seed-memory.md"
        content = seed.read_text()
        assert "# Seed Memory" in content
        assert "Inherited from Parent Organism" in content
        assert "NOT loaded into the context window" in content

    def test_seed_memory_has_detected_stack_section(self, tmp_path: Path):
        """seed-memory.md should include a Detected Stack section."""
        target = tmp_path / "test-app"
        target.mkdir()
        (target / "go.mod").write_text("module test\n\ngo 1.22\n")

        run_cos_init(target)

        seed = target / ".cognitive-os" / "seed-memory.md"
        content = seed.read_text()
        assert "## Detected Stack" in content
        assert "Keywords:" in content

    def test_seed_memory_has_inherited_knowledge_placeholder(self, tmp_path: Path):
        """seed-memory.md should have an Inherited Knowledge placeholder."""
        target = tmp_path / "test-app"
        target.mkdir()
        (target / "package.json").write_text('{}')

        run_cos_init(target)

        seed = target / ".cognitive-os" / "seed-memory.md"
        content = seed.read_text()
        assert "## Inherited Knowledge" in content
        assert "populate this section from Engram" in content


class TestPresets:
    """Verify preset files exist and have correct structure."""

    def test_startup_preset_exists(self):
        """startup.yaml preset should exist."""
        preset = PROJECT_ROOT / "presets" / "startup.yaml"
        assert preset.exists(), "presets/startup.yaml should exist"

    def test_enterprise_preset_exists(self):
        """enterprise.yaml preset should exist."""
        preset = PROJECT_ROOT / "presets" / "enterprise.yaml"
        assert preset.exists(), "presets/enterprise.yaml should exist"

    def test_startup_preset_has_lean_profile(self):
        """startup preset should use lean efficiency profile."""
        preset = PROJECT_ROOT / "presets" / "startup.yaml"
        content = preset.read_text()
        assert "efficiency_profile: lean" in content

    def test_enterprise_preset_has_full_profile(self):
        """enterprise preset should use full efficiency profile."""
        preset = PROJECT_ROOT / "presets" / "enterprise.yaml"
        content = preset.read_text()
        assert "efficiency_profile: full" in content

    def test_startup_preset_has_low_coverage(self):
        """startup preset should have lower coverage minimum."""
        preset = PROJECT_ROOT / "presets" / "startup.yaml"
        content = preset.read_text()
        assert "coverage_minimum: 50" in content

    def test_enterprise_preset_has_security_review(self):
        """enterprise preset should require security review."""
        preset = PROJECT_ROOT / "presets" / "enterprise.yaml"
        content = preset.read_text()
        assert "require_security_review: true" in content

    def test_enterprise_preset_has_audit_trail(self):
        """enterprise preset should require audit trail."""
        preset = PROJECT_ROOT / "presets" / "enterprise.yaml"
        content = preset.read_text()
        assert "require_audit_trail: true" in content


class TestProfileSuggestion:
    """cos init should suggest an efficiency profile based on project size."""

    def test_init_suggests_profile_for_small_project(self, tmp_path: Path):
        """Small projects without Docker should get lean suggestion."""
        target = tmp_path / "small-app"
        target.mkdir()
        (target / "main.go").write_text("package main\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        assert "lean" in result.stdout

    def test_init_suggests_startup_preset_for_small_project(self, tmp_path: Path):
        """Small projects without Docker should get startup preset suggestion."""
        target = tmp_path / "small-app"
        target.mkdir()
        (target / "main.go").write_text("package main\n")

        result = run_cos_init(target)

        assert result.returncode == 0
        assert "Suggested preset: startup" in result.stdout


class TestClaudeTemplate:
    """Verify CLAUDE.md.template includes First Session Protocol."""

    def test_template_has_first_session_protocol(self):
        """CLAUDE.md.template should include First Session Protocol section."""
        template = PROJECT_ROOT / "templates" / "CLAUDE.md.template"
        content = template.read_text()
        assert "## First Session Protocol" in content

    def test_template_mentions_seed_memory(self):
        """CLAUDE.md.template should mention seed-memory.md."""
        template = PROJECT_ROOT / "templates" / "CLAUDE.md.template"
        content = template.read_text()
        assert "seed-memory.md" in content

    def test_template_mentions_engram_search(self):
        """CLAUDE.md.template should instruct Engram search for inherited knowledge."""
        template = PROJECT_ROOT / "templates" / "CLAUDE.md.template"
        content = template.read_text()
        assert "mem_search" in content

    def test_installed_claude_md_has_first_session_protocol(self, tmp_path: Path):
        """After cos init, .claude/CLAUDE.md should have First Session Protocol."""
        target = tmp_path / "test-app"
        target.mkdir()

        run_cos_init(target)

        claude_md = target / ".claude" / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "First Session Protocol" in content
