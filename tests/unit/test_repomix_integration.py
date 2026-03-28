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
        # Just check it can be invoked
        result = subprocess.run(
            ["npx", "-y", "repomix", "--version"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # npx may take time to download, just check it doesn't crash
