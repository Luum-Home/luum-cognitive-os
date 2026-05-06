"""Registration tests for secret-detector launch coverage."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DRIVER = PROJECT_ROOT / "scripts/_lib/settings-driver-claude-code.sh"
ACTIVE_SETTINGS = PROJECT_ROOT / ".claude/settings.json"


def _secret_detector_matchers(settings: dict) -> list[str]:
    matchers: list[str] = []
    for group in settings.get("hooks", {}).get("PreToolUse", []):
        for hook in group.get("hooks", []):
            if "secret-detector.sh" in hook.get("command", ""):
                matchers.append(group.get("matcher", ""))
    return matchers


def test_secret_detector_registered_for_bash_edit_write_in_generated_claude_settings() -> None:
    generated = subprocess.check_output(["bash", str(DRIVER), "--emit"], text=True)
    settings = json.loads(generated)

    assert "Bash|Edit|Write" in _secret_detector_matchers(settings)


def test_secret_detector_registered_for_bash_edit_write_in_active_claude_settings() -> None:
    settings = json.loads(ACTIVE_SETTINGS.read_text(encoding="utf-8"))

    assert "Bash|Edit|Write" in _secret_detector_matchers(settings)


def test_registered_secret_detector_command_redacts_bash_payload(tmp_path: Path) -> None:
    """The generated registered command must execute the hook and redact Bash payloads."""
    settings = json.loads(subprocess.check_output(["bash", str(DRIVER), "--emit"], text=True))
    command = ""
    for group in settings["hooks"]["PreToolUse"]:
        if group.get("matcher") != "Bash|Edit|Write":
            continue
        for hook in group.get("hooks", []):
            if "secret-detector.sh" in hook.get("command", ""):
                command = hook["command"]
                break
    assert command

    payload = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo AKIAIOSFODNN7EXAMPLE && echo safe"},
        }
    )
    env = {"CLAUDE_PROJECT_DIR": str(PROJECT_ROOT)}
    result = subprocess.run(
        ["bash", "-lc", command],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout)
    updated = output["hookSpecificOutput"]["updatedInput"]["command"]
    assert "AKIAIOSFODNN7EXAMPLE" not in updated
    assert "[REDACTED]" in updated
    assert "echo safe" in updated
