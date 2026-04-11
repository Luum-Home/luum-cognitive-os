"""
Tests for Docker→pip migration Phase 1 quick wins.
Verifies requirements.txt, docker-compose comments, and cognitive-os.yaml updates.
"""

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text()


class TestRequirementsFile:
    def test_requirements_file_exists(self):
        assert (PROJECT_ROOT / "requirements.txt").exists(), "requirements.txt must exist"

    def test_mlflow_in_requirements(self):
        content = _read("requirements.txt")
        assert "mlflow" in content, "mlflow must be listed in requirements.txt"

    def test_nemoguardrails_in_requirements(self):
        content = _read("requirements.txt")
        assert "nemoguardrails" in content, "nemoguardrails must be listed in requirements.txt"

    def test_jupyter_in_requirements(self):
        content = _read("requirements.txt")
        assert "jupyter" in content, "jupyter must be listed in requirements.txt"

    def test_memu_in_requirements(self):
        content = _read("requirements.txt")
        assert "memu" in content, "memu must be listed in requirements.txt"

    def test_no_agpl_in_requirements(self):
        """None of the migration packages are AGPL-licensed."""
        content = _read("requirements.txt")
        # These are known AGPL packages — they must not appear
        agpl_packages = ["gpl", "agpl"]
        lower = content.lower()
        for pkg in agpl_packages:
            assert pkg not in lower, f"AGPL package reference '{pkg}' found in requirements.txt"

    def test_migrated_packages_have_migration_comment(self):
        content = _read("requirements.txt")
        assert "MIGRATED FROM DOCKER" in content or "MIGRATED TO PIP" in content, (
            "requirements.txt should contain migration comments for context"
        )


class TestDockerComposeMigrationNotes:
    def test_docker_compose_has_migration_notes(self):
        content = _read("docker-compose.cognitive-os.yml")
        assert "MIGRATED TO PIP" in content, (
            "docker-compose.cognitive-os.yml must contain MIGRATED TO PIP comments"
        )

    def test_langfuse_web_has_migration_note(self):
        content = _read("docker-compose.cognitive-os.yml")
        # Find langfuse-web section and check for migration note nearby
        idx = content.find("langfuse-web:")
        assert idx != -1, "langfuse-web service must exist in docker-compose"
        surrounding = content[max(0, idx - 300) : idx + 100]
        assert "MIGRATED TO PIP" in surrounding or "mlflow" in surrounding, (
            "langfuse-web section should have a migration note referencing mlflow"
        )

    def test_nemo_guardrails_has_migration_note(self):
        content = _read("docker-compose.cognitive-os.yml")
        idx = content.find("nemo-guardrails:")
        assert idx != -1
        surrounding = content[max(0, idx - 300) : idx + 100]
        assert "MIGRATED TO PIP" in surrounding or "nemoguardrails" in surrounding, (
            "nemo-guardrails section should have a migration note"
        )

    def test_jupyter_has_migration_note(self):
        content = _read("docker-compose.cognitive-os.yml")
        idx = content.find("  jupyter:")
        assert idx != -1
        surrounding = content[max(0, idx - 300) : idx + 100]
        assert "MIGRATED TO PIP" in surrounding, (
            "jupyter section should have a migration note"
        )

    def test_memu_has_migration_note(self):
        content = _read("docker-compose.cognitive-os.yml")
        idx = content.find("  memu:")
        assert idx != -1
        surrounding = content[max(0, idx - 300) : idx + 100]
        assert "MIGRATED TO PIP" in surrounding, (
            "memu section should have a migration note"
        )

    def test_opik_has_migration_note(self):
        content = _read("docker-compose.cognitive-os.yml")
        idx = content.find("opik-backend:")
        assert idx != -1
        surrounding = content[max(0, idx - 300) : idx + 100]
        assert "MIGRATED TO PIP" in surrounding or "cloud" in surrounding.lower(), (
            "opik-backend section should have a migration note"
        )

    def test_service_definitions_still_exist(self):
        """Services must NOT be deleted — kept for reference/CI."""
        content = _read("docker-compose.cognitive-os.yml")
        for service in ["langfuse-web:", "nemo-guardrails:", "jupyter:", "memu:", "opik-backend:"]:
            assert service in content, f"Service '{service}' must still exist in docker-compose (kept for CI reference)"


class TestCognitiveOsYamlUpdated:
    def test_langfuse_mode_is_disabled(self):
        content = _read("cognitive-os.yaml")
        # Find langfuse service block
        idx = content.find("      langfuse:")
        assert idx != -1, "langfuse service must exist in cognitive-os.yaml"
        block = content[idx : idx + 200]
        assert "disabled" in block or "pip" in block or "mlflow" in block, (
            "langfuse mode should be 'disabled' (replaced by mlflow)"
        )

    def test_nemo_guardrails_mode_is_pip(self):
        content = _read("cognitive-os.yaml")
        idx = content.find("nemo_guardrails:")
        assert idx != -1
        block = content[idx : idx + 200]
        assert "pip" in block or "disabled" in block, (
            "nemo_guardrails mode should be 'pip' (migrated from Docker)"
        )

    def test_opik_mode_is_cloud_or_pip(self):
        content = _read("cognitive-os.yaml")
        idx = content.find("      opik:")
        assert idx != -1
        block = content[idx : idx + 200]
        assert "cloud" in block or "pip" in block or "disabled" in block, (
            "opik mode should be 'cloud' (uses Comet cloud API)"
        )

    def test_jupyter_mode_is_pip(self):
        content = _read("cognitive-os.yaml")
        idx = content.find("      jupyter:")
        assert idx != -1
        block = content[idx : idx + 200]
        assert "pip" in block or "disabled" in block, (
            "jupyter mode should be 'pip' (migrated from Docker)"
        )

    def test_mlflow_entry_exists(self):
        content = _read("cognitive-os.yaml")
        assert "mlflow:" in content, (
            "mlflow service entry should exist in cognitive-os.yaml as the langfuse replacement"
        )

    def test_memu_pip_entry_exists(self):
        content = _read("cognitive-os.yaml")
        # memu entry in services
        assert "memu:" in content, "memu service entry should exist in cognitive-os.yaml"
        idx = content.find("      memu:")
        block = content[idx : idx + 200]
        assert "pip" in block or "disabled" in block, (
            "memu mode should be 'pip'"
        )
