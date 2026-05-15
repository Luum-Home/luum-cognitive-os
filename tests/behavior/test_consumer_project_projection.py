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
        ("agents-md", "AGENTS.md"),
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
        ("cline", ".clinerules/cognitive-os.md"),
        ("continue-dev", ".continue/rules/cognitive-os.md"),
        ("kilo-code", ".kilocode/rules/cognitive-os.md"),
        ("zed-ai", ".rules"),
        ("augment-code", ".augment/rules/cognitive-os.md"),
        ("goose", ".goosehints"),
        ("aider", "CONVENTIONS.md"),
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
    if harness == "agents-md":
        agents = (tmp_path / "AGENTS.md").read_text()
        assert "COGNITIVE_OS_AGENTS_MD_START" in agents
        assert "Cognitive OS for AGENTS.md-native tools" in agents
        assert "universal markdown baseline" in agents
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

    if harness == "cline":
        assert "Cognitive OS for Cline" in (tmp_path / ".clinerules/cognitive-os.md").read_text()
        assert (tmp_path / ".cline/README.md").is_file()
    if harness == "continue-dev":
        assert "alwaysApply: true" in (tmp_path / ".continue/rules/cognitive-os.md").read_text()
        assert json.loads((tmp_path / ".continue/mcpServers/cognitive-os.json").read_text()) == {"mcpServers": {}}
    if harness == "kilo-code":
        assert "COGNITIVE_OS_KILO_CODE_START" in (tmp_path / "AGENTS.md").read_text()
        assert "Cognitive OS for Kilo Code" in (tmp_path / ".kilocode/rules/cognitive-os.md").read_text()
        assert not (tmp_path / ".kilocode/mcp.json").exists()
        kilo = json.loads((tmp_path / ".kilo/kilo.jsonc").read_text())
        assert kilo["mcp"] == {}
        assert ".kilocode/rules/cognitive-os.md" in kilo["instructions"]
    if harness == "zed-ai":
        assert "Cognitive OS for Zed AI" in (tmp_path / ".rules").read_text()
        assert json.loads((tmp_path / ".zed/settings.json").read_text()) == {"context_servers": {}}
    if harness == "augment-code":
        assert "Cognitive OS for Augment" in (tmp_path / ".augment/rules/cognitive-os.md").read_text()
        assert json.loads((tmp_path / ".augment/mcp.json").read_text()) == {"mcpServers": {}}
        assert "--rules .augment/rules/cognitive-os.md" in (tmp_path / ".augment/README.md").read_text()
    if harness == "goose":
        assert "Cognitive OS for Goose" in (tmp_path / ".goosehints").read_text()
        assert not (tmp_path / ".goose/config.json").exists()
    if harness == "aider":
        assert "Cognitive OS for Aider" in (tmp_path / "CONVENTIONS.md").read_text()
        assert "CONVENTIONS.md" in (tmp_path / ".aider.conf.yml").read_text()
    if harness == "shell-ci":
        shell_meta = json.loads((tmp_path / ".cognitive-os/shell-ci-projection.json").read_text())
        assert shell_meta["commands_projected"] == 15
        assert (tmp_path / ".github/workflows/cognitive-os-shell-ci.yml").is_file()
        assert (tmp_path / "scripts/cos-status.sh").is_symlink()
    assert (tmp_path / ".cognitive-os" / "hooks" / "cos" / "session-init.sh").exists()
    assert (tmp_path / ".cognitive-os" / "rules" / "cos" / "RULES-COMPACT.md").exists()
    assert (tmp_path / ".cognitive-os" / "skills" / "cos" / "cos-status" / "SKILL.md").exists()


def test_codex_project_install_has_closed_hook_runtime_dependencies(tmp_path: Path) -> None:
    """Smoke: generated Codex project hooks must only reference installed, scope-allowed runtime paths."""
    install = subprocess.run(
        [sys.executable, str(COS_INIT), "--default", "--harness", "codex"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert install.returncode == 0, install.stderr + install.stdout

    audit = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "runtime_hook_reality.py"),
            "--project-root",
            str(tmp_path),
            "--settings",
            str(tmp_path / ".codex" / "hooks.json"),
            "--dependency-closure",
            "--install-scope",
            "project",
            "--fail-on-findings",
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert audit.returncode == 0, audit.stderr + audit.stdout
    payload = json.loads(audit.stdout)
    assert payload["summary"]["status"] == "pass"
    assert payload["findings"] == []
