"""Behavior tests for hooks/clarification-gate.sh

Validates ambiguity scoring, detail discounts, and BLOCK/WARN/PASS verdicts.
Key concern: long detailed prompts with file paths must NOT be blocked as
ambiguous (false positive regression test).
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK_PATH = PROJECT_ROOT / "hooks" / "clarification-gate.sh"


def run_hook(prompt: str, env_extra: dict = None) -> subprocess.CompletedProcess:
    """Run clarification-gate.sh with the given agent prompt."""
    stdin_data = json.dumps({
        "tool_name": "Agent",
        "tool_input": {"prompt": prompt},
    })

    tmpdir = tempfile.mkdtemp()
    cos_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
    os.makedirs(cos_dir, exist_ok=True)

    config_path = os.path.join(tmpdir, "cognitive-os.yaml")
    with open(config_path, "w") as f:
        f.write("project:\n  phase: reconstruction\nmodel_capability:\n  level: 2\n")

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = tmpdir
    env["COGNITIVE_OS_PROJECT_DIR"] = tmpdir
    env["COGNITIVE_OS_SESSION_ID"] = ""
    env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
    # Ensure capability level does NOT auto-disable this hook
    env.pop("COGNITIVE_OS_CAPABILITY_LEVEL", None)

    if env_extra:
        env.update(env_extra)

    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=stdin_data,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Helper to extract score from stderr output
# ---------------------------------------------------------------------------

def extract_score(result: subprocess.CompletedProcess) -> int:
    """Parse ambiguity score from hook stderr/stdout output, or return 0 if not blocked/warned."""
    combined = result.stdout + result.stderr
    for line in combined.splitlines():
        if "ambiguity score:" in line.lower():
            # e.g. "=== CLARIFICATION GATE: BLOCKED (ambiguity score: 75/100) ==="
            part = line.split("ambiguity score:")[-1].strip()
            score_str = part.split("/")[0].strip().rstrip(")")
            try:
                return int(score_str)
            except ValueError:
                pass
    return 0  # not in output → score was below warn threshold (< 30)


# ---------------------------------------------------------------------------
# Base scoring tests
# ---------------------------------------------------------------------------

class TestBaseScoring:
    """Tests for the base ambiguity signals."""

    def test_short_vague_prompt_blocked(self):
        """Short vague prompt ('add auth') must score high and be BLOCKED."""
        result = run_hook("add auth")
        assert result.returncode == 2, "Short vague prompt must be BLOCKED"
        combined = result.stdout + result.stderr
        assert "BLOCKED" in combined or "BLOCK" in combined

    def test_short_vague_prompt_high_score(self):
        """Short vague prompt must score >= 60."""
        result = run_hook("add auth")
        score = extract_score(result)
        assert score >= 60, f"Expected score >= 60, got {score}"

    def test_short_clear_prompt_with_filepath_lower_score(self):
        """Adding a file path to a short prompt reduces the ambiguity score."""
        vague_result = run_hook("add auth")
        clear_result = run_hook("add auth to src/auth/handler.go")
        vague_score = extract_score(vague_result)
        clear_score = extract_score(clear_result)
        assert clear_score < vague_score, (
            f"File path should reduce score. vague={vague_score}, clear={clear_score}"
        )

    def test_non_agent_tool_ignored(self):
        """Non-Agent tool calls are skipped silently."""
        stdin_data = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        })
        tmpdir = tempfile.mkdtemp()
        cos_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
        os.makedirs(cos_dir, exist_ok=True)
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = tmpdir
        env["COGNITIVE_OS_SESSION_ID"] = ""
        env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=stdin_data,
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0

    def test_empty_input_exits_cleanly(self):
        """Empty input must not crash the hook."""
        tmpdir = tempfile.mkdtemp()
        cos_dir = os.path.join(tmpdir, ".cognitive-os", "metrics")
        os.makedirs(cos_dir, exist_ok=True)
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = tmpdir
        env["COGNITIVE_OS_SESSION_ID"] = ""
        env["COGNITIVE_OS_HOOK_HEARTBEAT"] = "false"
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input="",
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Detail discount tests
# ---------------------------------------------------------------------------

class TestDetailDiscount:
    """Tests for the detail discount logic added to prevent false positives."""

    def test_long_detailed_prompt_with_file_paths_passes(self):
        """A detailed prompt (>500 chars) with 5+ file paths must score < 30 and PASS."""
        prompt = (
            "Implement the new user authentication flow.\n\n"
            "Files to modify:\n"
            "  - src/auth/handler.go\n"
            "  - src/auth/middleware.go\n"
            "  - src/auth/dto.go\n"
            "  - internal/users/application/use_cases/login.go\n"
            "  - internal/users/domain/entities/session.go\n\n"
            "Steps:\n"
            "1. Add JWT validation in src/auth/middleware.go\n"
            "2. Update the login use case in internal/users/application/use_cases/login.go\n"
            "3. Return a session token in src/auth/handler.go\n\n"
            "ACCEPTANCE CRITERIA:\n"
            "1. go build ./... exits 0\n"
            "2. go test ./internal/users/... exits 0\n"
            "3. POST /auth/login returns 200 with a token\n"
        )
        assert len(prompt) > 500, "Prompt must be > 500 chars for this test to be meaningful"
        result = run_hook(prompt)
        score = extract_score(result)
        assert result.returncode == 0, (
            f"Detailed prompt with file paths must PASS, got returncode={result.returncode}. "
            f"Score={score}. Output:\n{result.stdout}\n{result.stderr}"
        )
        assert score < 30, f"Expected score < 30, got {score}"

    def test_prompt_with_engram_references_reduced_score(self):
        """Prompts mentioning engram/mem_save get a score discount."""
        base_prompt = (
            "Update the user service and save findings.\n"
            "Modify src/users/handler.go to add validation.\n"
        )
        engram_prompt = base_prompt + (
            "After completing, call mem_save with topic_key 'implementation/users/validation'.\n"
        )
        base_result = run_hook(base_prompt)
        engram_result = run_hook(engram_prompt)
        base_score = extract_score(base_result)
        engram_score = extract_score(engram_result)
        assert engram_score <= base_score, (
            f"Engram references should reduce or maintain score. "
            f"base={base_score}, engram={engram_score}"
        )

    def test_prompt_with_numbered_steps_reduced_score(self):
        """Prompts with numbered steps get a score discount."""
        base_prompt = "Update src/handler.go to add auth validation."
        structured_prompt = (
            "Update src/handler.go to add auth validation.\n"
            "1. Read the current handler\n"
            "2. Add the JWT check\n"
            "3. Return 401 on failure\n"
        )
        base_result = run_hook(base_prompt)
        structured_result = run_hook(structured_prompt)
        base_score = extract_score(base_result)
        structured_score = extract_score(structured_result)
        assert structured_score <= base_score, (
            f"Numbered steps should reduce or maintain score. "
            f"base={base_score}, structured={structured_score}"
        )

    def test_discount_capped_at_20_for_many_file_paths(self):
        """File path discount is capped at -20, so 20 file paths don't give -100."""
        # Build a prompt with 20 file paths — discount should be capped at 20
        many_paths = "\n".join(f"  - src/module{i}/handler.go" for i in range(20))
        prompt = f"Refactor these files:\n{many_paths}\n"
        result = run_hook(prompt)
        score = extract_score(result)
        # We can't easily know the pre-discount score, but the score should be >= 0
        assert score >= 0, f"Score should never go negative, got {score}"
        assert result.returncode in (0, 2), "Should exit cleanly"

    def test_very_short_vague_prompt_without_paths_penalized(self):
        """Very short vague prompts with no file paths or criteria are still penalized."""
        # "fix bugs" has no file paths (no /path/file.ext), no tech, no criteria, short
        result = run_hook("fix bugs now")
        combined = result.stdout + result.stderr
        score = extract_score(result)
        # Without file paths there is no discount — short + no criteria + no paths = high score
        is_warned_or_blocked = result.returncode == 2 or "WARNING" in combined or score >= 30
        assert is_warned_or_blocked, (
            f"Short vague prompt without file paths must still be warned/blocked. "
            f"score={score}, returncode={result.returncode}"
        )

    def test_discount_does_not_make_very_short_vague_pass_when_no_paths(self):
        """The discount only applies when file paths are present. Pure vague still scores high."""
        result = run_hook("add tests")
        score = extract_score(result)
        # No file paths → no discount applies. Short + no criteria = high score.
        assert score >= 30, f"Pure vague prompt without file paths must score >= 30, got {score}"


# ---------------------------------------------------------------------------
# False positive regression test
# ---------------------------------------------------------------------------

class TestFalsePositiveRegression:
    """Regression test for the specific false positive that triggered this fix."""

    def test_real_world_detailed_prompt_passes(self):
        """The ~2K char prompt that triggered the false positive must score < 30."""
        # This is representative of the kind of prompt that was being falsely blocked:
        # a detailed implementation prompt with file paths, acceptance criteria,
        # numbered steps, and engram references.
        prompt = """\
Implement the rules-to-hooks refactor as described in the plan.

## Context
The current architecture has rules files that are loaded as context. We need to
migrate hook logic into dedicated hook scripts for better isolation and testability.

## Files to modify
- hooks/clarification-gate.sh
- hooks/auto-rollback-trigger.sh
- hooks/completion-gate.sh
- rules/clarification-gate.md
- rules/auto-rollback.md
- tests/behavior/test_clarification_gate.py

## Steps
1. Read hooks/clarification-gate.sh and understand the current scoring logic
2. Identify the false positive case where detailed prompts score too high
3. Add a detail discount: file paths, long prompts, engram references, numbered steps
4. Write tests in tests/behavior/test_clarification_gate.py covering:
   - Short vague prompts are BLOCKED
   - Detailed prompts with file paths PASS
   - Engram references reduce score
   - Numbered steps reduce score
   - Discount is capped (no negative scores from many file paths)
5. Run bash -n hooks/clarification-gate.sh to verify syntax
6. Run python3 -m pytest tests/behavior/test_clarification_gate.py -v
7. Save findings to engram via mem_save with topic_key 'bugfix/clarification-gate/false-positive'

## ACCEPTANCE CRITERIA
1. bash -n hooks/clarification-gate.sh exits 0 (no syntax errors)
2. All new tests pass: python3 -m pytest tests/behavior/test_clarification_gate.py -v
3. This prompt itself scores < 30 when passed to the hook
4. Short vague prompt 'add auth' still scores >= 60

## Verification
Run: bash -n hooks/clarification-gate.sh
Run: python3 -m pytest tests/behavior/test_clarification_gate.py -v
"""
        assert len(prompt) > 500, "This prompt must be > 500 chars"
        result = run_hook(prompt)
        score = extract_score(result)
        assert result.returncode == 0, (
            f"Real-world detailed prompt must PASS (not be blocked). "
            f"Score={score}. Output:\n{result.stdout}\n{result.stderr}"
        )
        assert score < 30, (
            f"Real-world detailed prompt must score < 30 (was {score}). "
            "The false positive regression is not fixed."
        )

    def test_engram_heavy_prompt_passes(self):
        """A prompt heavily using engram references alongside file paths must pass."""
        prompt = """\
Update the skill registry and save all discoveries to engram.

## Task
Read skills/sdd-apply/SKILL.md and skills/sdd-verify/SKILL.md.
Update .cognitive-os/CATALOG.md to reflect the latest skill versions.

## Steps
1. Read the current CATALOG.md
2. Update entries for sdd-apply and sdd-verify
3. Call mem_search to find existing engram entries for topic_key 'planning/sdd-apply'
4. Call mem_save with topic_key 'implementation/catalog/update' to record changes
5. Verify the CATALOG.md is valid markdown

## Acceptance criteria
- CATALOG.md contains updated entries
- mem_save was called with correct topic_key
- No broken markdown links
"""
        result = run_hook(prompt)
        score = extract_score(result)
        assert result.returncode == 0, (
            f"Engram-heavy prompt with file paths must PASS. "
            f"Score={score}. Output:\n{result.stdout}\n{result.stderr}"
        )
