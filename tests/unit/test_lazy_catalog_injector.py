"""
tests/unit/test_lazy_catalog_injector.py

Behavioral tests for lazy-catalog-injector.sh.

Tests verify:
- Trigger keywords cause catalog injection (stdout contains catalog content)
- Non-trigger prompts produce no output
- COS_LAZY_CATALOG=0 suppresses injection (hook is a no-op)
- Missing catalog exits cleanly
- Telemetry record is written on injection
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "lazy-catalog-injector.sh"
CATALOG = PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md"


def run_hook(prompt: str, env_overrides: dict | None = None, catalog_path: str | None = None) -> subprocess.CompletedProcess:
    """Run lazy-catalog-injector.sh with a given prompt and env."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env.pop("COS_LAZY_CATALOG", None)  # default: lazy ON

    # Build CLAUDE_TOOL_INPUT JSON
    payload = json.dumps({"prompt": prompt})
    env["CLAUDE_TOOL_INPUT"] = payload

    if catalog_path is not None:
        env["CLAUDE_PROJECT_DIR"] = catalog_path

    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK)],
        capture_output=True,
        text=True,
        env=env,
        timeout=5,
    )


@pytest.mark.skipif(not HOOK.exists(), reason="lazy-catalog-injector.sh not found")
@pytest.mark.skipif(not CATALOG.exists(), reason="CATALOG-COMPACT.md not found")
class TestLazyCatalogInjector:

    def test_skill_keyword_triggers_injection(self):
        """Prompt containing '/skill' causes CATALOG-COMPACT content in output."""
        result = run_hook("what /skill can I use for this?")
        assert result.returncode == 0, result.stderr
        assert "CATALOG-COMPACT" in result.stdout

    def test_available_skills_triggers_injection(self):
        """'available skills' phrase triggers injection."""
        result = run_hook("show me available skills for code review")
        assert result.returncode == 0
        assert "CATALOG-COMPACT" in result.stdout

    def test_list_skills_triggers_injection(self):
        """'list skills' phrase triggers injection."""
        result = run_hook("can you list skills related to testing?")
        assert result.returncode == 0
        assert "CATALOG-COMPACT" in result.stdout

    def test_non_trigger_prompt_produces_no_output(self):
        """A plain coding question does not trigger catalog injection."""
        result = run_hook("please fix the bug in my authentication module")
        assert result.returncode == 0
        # No catalog header in output
        assert "CATALOG-COMPACT" not in result.stdout

    def test_non_trigger_generic_prompt_silent(self):
        """Generic prompt produces empty stdout."""
        result = run_hook("what is the capital of France?")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_cos_lazy_catalog_zero_suppresses_injection(self):
        """COS_LAZY_CATALOG=0 makes the hook a no-op even on skill keywords."""
        result = run_hook(
            "list skills available",
            env_overrides={"COS_LAZY_CATALOG": "0"},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_cos_lazy_catalog_one_is_active(self):
        """COS_LAZY_CATALOG=1 (explicit) still triggers injection."""
        result = run_hook(
            "/skill router help",
            env_overrides={"COS_LAZY_CATALOG": "1"},
        )
        assert result.returncode == 0
        assert "CATALOG-COMPACT" in result.stdout

    def test_missing_catalog_exits_cleanly(self, tmp_path):
        """Hook exits 0 when CATALOG-COMPACT.md is absent."""
        result = run_hook(
            "list skills",
            catalog_path=str(tmp_path),
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_empty_prompt_exits_cleanly(self):
        """Empty prompt exits 0 with no output."""
        result = run_hook("")
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_telemetry_written_on_injection(self, tmp_path):
        """Injection event is appended to skill-discovery.jsonl."""
        # Set up a tmp project dir with a fake catalog
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "CATALOG-COMPACT.md").write_text("# Fake Catalog\n- **test-skill** — does testing\n")

        runtime_dir = tmp_path / ".cognitive-os" / "runtime"
        runtime_dir.mkdir(parents=True)

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        env["CLAUDE_TOOL_INPUT"] = json.dumps({"prompt": "what skills are available?"})
        env.pop("COS_LAZY_CATALOG", None)

        result = subprocess.run(
            ["bash", str(HOOK)],
            capture_output=True, text=True, env=env, timeout=5,
        )
        assert result.returncode == 0

        telemetry_path = runtime_dir / "skill-discovery.jsonl"
        assert telemetry_path.exists(), "skill-discovery.jsonl not created"
        lines = [l for l in telemetry_path.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        record = json.loads(lines[-1])
        assert record["event"] == "catalog_injected"
        assert record["lazy_catalog_active"] is True
        assert record["trigger_match"] is True
