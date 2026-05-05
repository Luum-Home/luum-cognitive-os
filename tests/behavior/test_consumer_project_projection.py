from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
COS_INIT = REPO_ROOT / "scripts" / "cos_init.py"


@pytest.mark.parametrize(
    ("harness", "settings_file"),
    [
        ("claude", ".claude/settings.json"),
        ("codex", ".codex/hooks.json"),
        ("opencode", "opencode.json"),
        ("vscode-copilot", ".github/copilot-instructions.md"),
        ("cursor", ".cursor/rules/cognitive-os.mdc"),
        ("qwen-code", ".qwen/settings.json"),
        ("kimi-code", "AGENTS.md"),
        ("gemini-cli", ".gemini/settings.json"),
        ("warp", "AGENTS.md"),
        ("amp-code", "AGENTS.md"),
        ("jetbrains-junie", ".junie/AGENTS.md"),
        ("qoder", "AGENTS.md"),
        ("factory-droid", "AGENTS.md"),
        ("shell-ci", ".cognitive-os/shell-ci-projection.json"),
    ],
)
def test_default_install_projects_core_primitives_into_consumer_project(tmp_path: Path, harness: str, settings_file: str) -> None:
    result = subprocess.run(
        [sys.executable, str(COS_INIT), "--default", "--harness", harness],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    install_meta = json.loads((tmp_path / ".cognitive-os" / "install-meta.json").read_text())
    assert install_meta["harness"] == harness
    assert install_meta["rules_installed"] >= 13
    assert install_meta["hooks_installed"] >= 37
    assert install_meta["skills_installed"] >= 8
    assert (tmp_path / settings_file).exists()
    if harness == "opencode":
        opencode = json.loads((tmp_path / "opencode.json").read_text())
        assert ".cognitive-os/rules/cos/RULES-COMPACT.md" in opencode["instructions"]
        assert opencode["permission"]["bash"] == "ask"
    if harness == "vscode-copilot":
        assert "Cognitive OS" in (tmp_path / ".github/copilot-instructions.md").read_text()
        assert json.loads((tmp_path / ".vscode/mcp.json").read_text()) == {"servers": {}}
    if harness == "cursor":
        assert "alwaysApply: true" in (tmp_path / ".cursor/rules/cognitive-os.mdc").read_text()
        assert json.loads((tmp_path / ".cursor/mcp.json").read_text()) == {"mcpServers": {}}
    if harness == "qwen-code":
        qwen_settings = json.loads((tmp_path / ".qwen/settings.json").read_text())
        assert qwen_settings["context"]["fileName"] == ["QWEN.md", "AGENTS.md", ".cognitive-os/rules/cos/RULES-COMPACT.md"]
        assert ".cognitive-os/skills/cos" in qwen_settings["context"]["includeDirectories"]
        assert qwen_settings["mcpServers"] == {}
        assert qwen_settings["tools"]["approvalMode"] == "default"
        assert "Cognitive OS" in (tmp_path / "QWEN.md").read_text()
    if harness == "kimi-code":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_KIMI_START" in agents
        assert "Cognitive OS for Kimi Code CLI" in agents
        assert json.loads((tmp_path / ".kimi/mcp.json").read_text()) == {"mcpServers": {}}
        assert "--mcp-config-file .kimi/mcp.json" in (tmp_path / ".kimi/README.md").read_text()

    if harness == "gemini-cli":
        gemini = json.loads((tmp_path / ".gemini/settings.json").read_text())
        assert gemini["contextFileName"] == ["GEMINI.md", "AGENTS.md"]
        assert ".cognitive-os/rules/cos" in gemini["includeDirectories"]
        assert gemini["mcpServers"] == {}
        assert gemini["autoAccept"] is False
        assert "Cognitive OS" in (tmp_path / "GEMINI.md").read_text()
    if harness == "warp":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_WARP_START" in agents
        assert "Cognitive OS for Warp Agent" in agents
        assert "WARP.md" in agents
        assert (tmp_path / ".warp/README.md").is_file()
    if harness == "amp-code":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_AMP_START" in agents
        assert "Cognitive OS for Amp" in agents
        assert json.loads((tmp_path / ".amp/settings.json").read_text()) == {"amp.mcpServers": {}}
    if harness == "jetbrains-junie":
        junie = (tmp_path / ".junie/AGENTS.md").read_text()
        assert "Cognitive OS for JetBrains Junie" in junie
        assert "RULES-COMPACT.md" in junie
        assert (tmp_path / ".junie/README.md").is_file()
    if harness == "qoder":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_QODER_START" in agents
        assert json.loads((tmp_path / ".mcp.json").read_text()) == {"mcpServers": {}}
        assert json.loads((tmp_path / ".qoder/settings.json").read_text())["permissions"]["deny"] == []
    if harness == "factory-droid":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_FACTORY_DROID_START" in agents
        assert json.loads((tmp_path / ".factory/mcp.json").read_text()) == {"mcpServers": {}}
        assert json.loads((tmp_path / ".factory/settings.json").read_text()) == {"hooks": {}}
        assert "name: cognitive-os" in (tmp_path / ".factory/skills/cognitive-os/SKILL.md").read_text()
    if harness == "shell-ci":
        shell_meta = json.loads((tmp_path / ".cognitive-os/shell-ci-projection.json").read_text())
        assert shell_meta["commands_projected"] == 15
        assert (tmp_path / ".github/workflows/cognitive-os-shell-ci.yml").is_file()
        assert (tmp_path / "scripts/cos-status.sh").is_symlink()
    assert (tmp_path / ".cognitive-os" / "hooks" / "cos" / "session-init.sh").exists()
    assert (tmp_path / ".cognitive-os" / "rules" / "cos" / "RULES-COMPACT.md").exists()
    assert (tmp_path / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").exists()
