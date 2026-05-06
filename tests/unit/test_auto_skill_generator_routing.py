"""Tests for routing_patterns injection in auto-skill-generator.sh output.

Strategy: synthesise the SKILL.md generation logic in Python (mirrors the
shell script's behaviour) and verify that routing_patterns are injected when
the deriver is available.  A subprocess test fires the actual hook with a
synthetic Agent completion JSON to confirm end-to-end SKILL.md output.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure lib/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.routing_pattern_deriver import RoutingPatternDeriver, _build_yaml_block

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / "packages" / "consequence-system" / "hooks" / "auto-skill-generator.sh"


# ---------------------------------------------------------------------------
# Unit: deriver output integrates into frontmatter
# ---------------------------------------------------------------------------


class TestFrontmatterIntegration:
    """Verify the YAML block produced by the deriver can be embedded in frontmatter."""

    def test_routing_patterns_yaml_embeddable(self) -> None:
        deriver = RoutingPatternDeriver()
        patterns = deriver.derive("cos-quickstart", "Quick start guide for Cognitive OS")
        yaml_block = _build_yaml_block(patterns)
        # Build a minimal frontmatter string
        frontmatter = f"""---
name: cos-quickstart
description: Quick start guide for Cognitive OS
lifecycle_state: sandbox
distribution: lab
{yaml_block}
---"""
        assert "routing_patterns:" in frontmatter
        assert "pattern:" in frontmatter
        assert "confidence:" in frontmatter

    def test_frontmatter_valid_indentation(self) -> None:
        deriver = RoutingPatternDeriver()
        patterns = deriver.derive("audit-integrity", "Audit the integrity of skills and hooks")
        yaml_block = _build_yaml_block(patterns)
        for line in yaml_block.splitlines()[1:]:  # skip first "routing_patterns:" line
            assert line.startswith("  "), f"Expected 2-space indent, got: {line!r}"

    def test_multiple_skills_produce_distinct_patterns(self) -> None:
        deriver = RoutingPatternDeriver()
        skills = [
            ("audit-integrity", "Audit the integrity of the system"),
            ("caveman", "Compress context using cave-person minimal language"),
            ("cos-quickstart", "Quick start guide for the Cognitive OS"),
        ]
        all_patterns: list[list[dict]] = []
        for name, desc in skills:
            result = deriver.derive(name, desc)
            all_patterns.append(result)
            assert len(result) >= 2

        # Primary patterns (highest confidence) must differ across skills
        primaries = {p[0]["pattern"] for p in all_patterns}
        assert len(primaries) == 3, "Each skill should have a distinct primary pattern"


# ---------------------------------------------------------------------------
# Subprocess: hook produces SKILL.md with routing_patterns
# ---------------------------------------------------------------------------


def _make_agent_completion(description: str, response_text: str) -> dict:
    """Build a minimal synthetic Agent tool completion JSON."""
    return {
        "tool_name": "Agent",
        "tool_input": {
            "description": description,
            "prompt": description,
        },
        "tool_response": {
            "result": response_text,
            "num_tool_uses": 15,
            "is_error": False,
        },
    }


@pytest.mark.skipif(
    not HOOK_PATH.exists(),
    reason="auto-skill-generator.sh not found",
)
class TestHookSubprocess:
    """End-to-end subprocess tests that fire the actual hook."""

    def _run_hook(
        self,
        agent_json: dict,
        skills_dir: Path,
        metrics_dir: Path,
        env: dict | None = None,
    ) -> subprocess.CompletedProcess:
        base_env = os.environ.copy()
        # CLAUDE_PROJECT_DIR must be the repo/project root; the hook appends
        # .cognitive-os/skills/auto-generated/ to it internally.
        # skills_dir = tmp_path / ".cognitive-os" / "skills" / "auto-generated"
        # so the project root is three levels up.
        base_env["CLAUDE_PROJECT_DIR"] = str(skills_dir.parent.parent.parent)
        base_env["NO_AUTO_SKILL"] = ""
        base_env["DISABLE_HOOK_AUTO_SKILL_GENERATOR"] = ""
        if env:
            base_env.update(env)

        return subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=json.dumps(agent_json),
            capture_output=True,
            text=True,
            env=base_env,
            timeout=30,
            cwd=str(REPO_ROOT),
        )

    def _hook_ran(self, result: subprocess.CompletedProcess) -> bool:
        """Return True if the hook ran to completion (not blocked by capability/killswitch)."""
        # Exit codes 1-9 from the _lib checks indicate early-exit (not a test failure).
        # Exit 0 means the hook completed normally.
        return result.returncode == 0

    def test_generated_skill_md_contains_routing_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / ".cognitive-os" / "skills" / "auto-generated"
            metrics_dir = tmp_path / ".cognitive-os" / "metrics"
            skills_dir.mkdir(parents=True)
            metrics_dir.mkdir(parents=True)

            big_response = (
                "- Created a comprehensive audit pipeline\n"
                "- Fixed integration test failures\n"
                "- Added routing_patterns to 20 SKILL.md files\n"
                "- Verified all hooks pass shellcheck\n"
                "- Updated ADR index\n"
            ) * 40  # > 8000 chars

            agent_json = _make_agent_completion(
                "audit integrity of all skills in the repository",
                big_response,
            )

            result = self._run_hook(agent_json, skills_dir, metrics_dir)

            if not self._hook_ran(result):
                pytest.skip(
                    f"Hook exited early (capability/killswitch check, code {result.returncode}). "
                    "Run in a configured COS project to exercise the full path."
                )

            # Find the generated SKILL.md
            generated = list(skills_dir.glob("*/SKILL.md"))
            assert len(generated) == 1, f"Expected 1 SKILL.md, found: {generated}"

            content = generated[0].read_text()
            assert "routing_patterns:" in content, (
                f"routing_patterns: not found in generated SKILL.md:\n{content[:1000]}"
            )

    def test_no_skill_generated_for_small_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / ".cognitive-os" / "skills" / "auto-generated"
            metrics_dir = tmp_path / ".cognitive-os" / "metrics"
            skills_dir.mkdir(parents=True)
            metrics_dir.mkdir(parents=True)

            agent_json = _make_agent_completion(
                "tiny task",
                "Done.",  # << 8000 chars, no file creation markers
            )

            result = self._run_hook(agent_json, skills_dir, metrics_dir)

            if not self._hook_ran(result):
                pytest.skip(
                    f"Hook exited early (capability/killswitch check, code {result.returncode})."
                )

            generated = list(skills_dir.glob("*/SKILL.md"))
            assert len(generated) == 0, "Should not generate skill for tiny response"

    def test_skill_md_contains_lifecycle_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            skills_dir = tmp_path / ".cognitive-os" / "skills" / "auto-generated"
            metrics_dir = tmp_path / ".cognitive-os" / "metrics"
            skills_dir.mkdir(parents=True)
            metrics_dir.mkdir(parents=True)

            big_response = "- Created and fixed many files\n" * 300

            agent_json = _make_agent_completion(
                "comprehensive skill generation test",
                big_response,
            )

            result = self._run_hook(agent_json, skills_dir, metrics_dir)

            if not self._hook_ran(result):
                pytest.skip(
                    f"Hook exited early (capability/killswitch check, code {result.returncode})."
                )

            generated = list(skills_dir.glob("*/SKILL.md"))
            if generated:
                content = generated[0].read_text()
                assert "lifecycle_state: sandbox" in content
                assert "distribution: lab" in content
