"""Unit tests for Repomix integration."""
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


class TestRepomixRule:
    def test_rule_file_exists(self):
        assert Path("rules/repomix-integration.md").exists()

    def test_rule_mentions_mcp(self):
        content = Path("rules/repomix-integration.md").read_text()
        assert "MCP" in content
        assert "repomix --mcp" in content

    def test_rule_mentions_compression(self):
        content = Path("rules/repomix-integration.md").read_text()
        assert "tree-sitter" in content
        assert "compress" in content.lower()


class TestRepomixConfig:
    def test_config_in_yaml(self):
        content = Path("cognitive-os.yaml").read_text()
        assert "repomix:" in content


class TestRepomixAvailability:
    def test_repomix_installed(self):
        if not shutil.which("repomix") and not shutil.which("npx"):
            pytest.skip("repomix/npx not installed")
        result = subprocess.run(
            ["npx", "-y", "repomix", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"repomix --version exited {result.returncode}:\n"
            f"stdout: {result.stdout[:200]}\nstderr: {result.stderr[:200]}"
        )
        # Version string must contain a digit (e.g. "0.2.35" or "1.0.0")
        output = result.stdout.strip() + result.stderr.strip()
        assert any(c.isdigit() for c in output), f"--version output has no digits: {output[:100]}"
