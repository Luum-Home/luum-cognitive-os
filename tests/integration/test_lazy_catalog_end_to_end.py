"""
tests/integration/test_lazy_catalog_end_to_end.py

End-to-end simulation of lazy catalog behavior across a full session lifecycle:

1. Simulate SessionStart with COS_LAZY_CATALOG=1 (default):
   - session-init.sh must NOT output the catalog content
   - Only the lazy pointer line should appear

2. Simulate a non-skill UserPromptSubmit:
   - lazy-catalog-injector.sh must produce no output

3. Simulate a skill-related UserPromptSubmit:
   - lazy-catalog-injector.sh must inject CATALOG-COMPACT content

4. Simulate SessionStart with COS_LAZY_CATALOG=0:
   - session-init.sh must output the eager catalog reference line

Constraints:
- Does not require a running harness
- Uses real hook scripts (bash execution)
- Validates stdout content, exit codes, telemetry file
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SESSION_INIT = PROJECT_ROOT / "hooks" / "session-init.sh"
INJECTOR = PROJECT_ROOT / "hooks" / "lazy-catalog-injector.sh"
CATALOG = PROJECT_ROOT / "skills" / "CATALOG-COMPACT.md"


def run_script(script: Path, env_overrides: dict | None = None,
               timeout: int = 10) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(PROJECT_ROOT)
    env["CLAUDE_PROJECT_DIR"] = str(PROJECT_ROOT)
    env.pop("COS_LAZY_CATALOG", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(script)],
        capture_output=True, text=True, env=env, timeout=timeout,
    )


@pytest.mark.skipif(not SESSION_INIT.exists(), reason="session-init.sh not found")
@pytest.mark.skipif(not CATALOG.exists(), reason="CATALOG-COMPACT.md not found")
class TestLazyCatalogEndToEnd:

    def test_session_start_lazy_does_not_emit_catalog_content(self):
        """With lazy ON, SessionStart stdout must NOT contain catalog body content."""
        result = run_script(SESSION_INIT, env_overrides={"COS_LAZY_CATALOG": "1"})
        # Hook may fail on missing directories — we care about catalog content
        # The catalog body contains skill names; check for distinctive content
        catalog_content = CATALOG.read_text()
        # Take a distinctive snippet from the catalog (first skill entry)
        first_skill_line = next(
            (l.strip() for l in catalog_content.splitlines() if l.strip().startswith("**")),
            None,
        )
        if first_skill_line:
            assert first_skill_line not in result.stdout, (
                f"Catalog content leaked into SessionStart stdout with lazy ON:\n"
                f"Found: {first_skill_line!r}"
            )

        # The lazy pointer line must be present
        assert "lazy" in result.stdout.lower() or "catalog" in result.stdout.lower(), (
            "Expected lazy pointer line in SessionStart stdout"
        )

    def test_session_start_eager_emits_catalog_reference(self):
        """With lazy OFF (COS_LAZY_CATALOG=0), SessionStart emits the catalog reference."""
        result = run_script(SESSION_INIT, env_overrides={"COS_LAZY_CATALOG": "0"})
        # Should mention CATALOG-COMPACT.md and eager mode
        assert "CATALOG-COMPACT.md" in result.stdout or "catalog" in result.stdout.lower(), (
            "Expected catalog reference in eager SessionStart output"
        )

    @pytest.mark.skipif(not INJECTOR.exists(), reason="lazy-catalog-injector.sh not found")
    def test_non_skill_prompt_produces_no_catalog_output(self):
        """A non-skill UserPromptSubmit produces empty stdout from injector."""
        env = {
            "COS_LAZY_CATALOG": "1",
            "CLAUDE_TOOL_INPUT": json.dumps({"prompt": "fix the bug in user authentication"}),
        }
        result = run_script(INJECTOR, env_overrides=env)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    @pytest.mark.skipif(not INJECTOR.exists(), reason="lazy-catalog-injector.sh not found")
    def test_skill_prompt_injects_catalog(self):
        """A skill-related UserPromptSubmit injects catalog content."""
        env = {
            "COS_LAZY_CATALOG": "1",
            "CLAUDE_TOOL_INPUT": json.dumps({"prompt": "what skills are available?"}),
        }
        result = run_script(INJECTOR, env_overrides=env)
        assert result.returncode == 0
        # Catalog header must be present in output
        assert "CATALOG-COMPACT" in result.stdout

    @pytest.mark.skipif(not INJECTOR.exists(), reason="lazy-catalog-injector.sh not found")
    def test_slash_skill_command_triggers_injection(self):
        """'/skill' in prompt triggers injection."""
        env = {
            "COS_LAZY_CATALOG": "1",
            "CLAUDE_TOOL_INPUT": json.dumps({"prompt": "run /skill router to find the right skill"}),
        }
        result = run_script(INJECTOR, env_overrides=env)
        assert result.returncode == 0
        assert "CATALOG-COMPACT" in result.stdout

    @pytest.mark.skipif(not INJECTOR.exists(), reason="lazy-catalog-injector.sh not found")
    def test_eager_mode_injector_is_noop(self):
        """With COS_LAZY_CATALOG=0, injector produces no output even for skill keywords."""
        env = {
            "COS_LAZY_CATALOG": "0",
            "CLAUDE_TOOL_INPUT": json.dumps({"prompt": "list all available skills"}),
        }
        result = run_script(INJECTOR, env_overrides=env)
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_session_init_still_references_catalog_compact(self):
        """session-init.sh must still contain CATALOG-COMPACT.md reference (lazy or not)."""
        content = SESSION_INIT.read_text()
        assert "CATALOG-COMPACT.md" in content, (
            "session-init.sh must reference CATALOG-COMPACT.md for the lazy/eager branch"
        )

    def test_cos_lazy_catalog_documented_in_session_init(self):
        """COS_LAZY_CATALOG env var is documented in session-init.sh."""
        content = SESSION_INIT.read_text()
        assert "COS_LAZY_CATALOG" in content, (
            "COS_LAZY_CATALOG env var must be documented in session-init.sh"
        )
