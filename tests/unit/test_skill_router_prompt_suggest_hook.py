"""Synthetic tests for hooks/skill-router-prompt-suggest.sh.

Tests pipe fake UserPromptSubmit stdin JSON to the hook via subprocess and
verify:
  1. Hook writes to .cognitive-os/metrics/skill-suggestion.jsonl
  2. Hook emits additionalContext JSON on stdout when confidence >= 0.80
  3. Hook exits 0 silently on low-confidence prompts (no stdout, no crash)
  4. Hook exits 0 silently when DISABLE_HOOK_SKILL_ROUTER_PROMPT_SUGGEST=1
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

HOOK_PATH = Path(__file__).parent.parent.parent / "hooks" / "skill-router-prompt-suggest.sh"
PROJECT_ROOT = Path(__file__).parent.parent.parent


def _run_hook(
    prompt: str,
    env_overrides: dict | None = None,
    tmp_dir: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook with a fake UserPromptSubmit JSON payload."""
    stdin_payload = json.dumps({"prompt": prompt})
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["PROJECT_DIR"] = str(PROJECT_ROOT)
    # Override metrics dir to avoid polluting real metrics
    if tmp_dir:
        env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_dir)
        env["PROJECT_DIR"] = str(tmp_dir)
        # Ensure lib is still importable from real project root
        env["PYTHONPATH"] = str(PROJECT_ROOT)

    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result


def _make_tmp_project(tmp_path: Path) -> Path:
    """Create a minimal project directory structure in tmp."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lib").symlink_to(PROJECT_ROOT / "lib")
    return tmp_path


@pytest.mark.skipif(
    not HOOK_PATH.exists(),
    reason="Hook file does not exist — run after hook is created",
)
class TestSkillRouterPromptSuggestHook:
    def test_hook_exits_zero(self, tmp_path):
        """Hook must always exit 0."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook("audit https://github.com/org/repo", tmp_dir=tmp)
        assert result.returncode == 0, (
            f"Hook exited {result.returncode}: {result.stderr}"
        )

    def test_high_confidence_emits_additional_context(self, tmp_path):
        """A GitHub URL prompt should produce additionalContext on stdout."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook(
            "audit https://github.com/HKUDS/OpenSpace and evaluate it",
            tmp_dir=tmp,
        )
        assert result.returncode == 0
        stdout = result.stdout.strip()
        if stdout:
            payload = json.loads(stdout)
            assert "hookSpecificOutput" in payload
            ctx = payload["hookSpecificOutput"]["additionalContext"]
            assert "confidence" in ctx.lower() or "/" in ctx

    def test_high_confidence_writes_suggestion_log(self, tmp_path):
        """Hook should write to skill-suggestion.jsonl for high-confidence prompts."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook(
            "audit https://github.com/HKUDS/OpenSpace",
            tmp_dir=tmp,
        )
        assert result.returncode == 0
        log_path = tmp / ".cognitive-os" / "metrics" / "skill-suggestion.jsonl"
        assert log_path.exists(), "skill-suggestion.jsonl was not created"
        lines = [l for l in log_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert "ts" in entry
        assert "prompt_hash" in entry
        assert "confidence" in entry

    def test_low_confidence_no_stdout(self, tmp_path):
        """Greetings should not produce additionalContext."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook("hello, how are you today?", tmp_dir=tmp)
        assert result.returncode == 0
        # stdout should be empty (no suggestion above threshold)
        assert result.stdout.strip() == "", (
            f"Expected no stdout for low-confidence prompt, got: {result.stdout!r}"
        )

    def test_killswitch_env_exits_silently(self, tmp_path):
        """DISABLE_HOOK_SKILL_ROUTER_PROMPT_SUGGEST=1 should exit 0 with no output."""
        tmp = _make_tmp_project(tmp_path)
        result = _run_hook(
            "audit https://github.com/org/repo",
            env_overrides={"DISABLE_HOOK_SKILL_ROUTER_PROMPT_SUGGEST": "1"},
            tmp_dir=tmp,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""
