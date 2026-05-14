"""Tests for the Reproduction system (memory inheritance during project spawning)."""

import os
import subprocess
from pathlib import Path
from typing import Optional


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


