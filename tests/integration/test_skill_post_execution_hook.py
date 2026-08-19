"""Integration tests for the skill post-execution analysis hook — ADR-176.

PAYLOAD PROVENANCE (2026-08-19). These tests used to feed a payload shaped
``{"skill_name": ..., "tool_response": {"tool_count", "duration_ms",
"tool_issues"}}``. The Claude Code harness sends none of those field names, so
the suite stayed green for 3.5 months over a hook that wrote nothing: 182
recorded invocations, ``.cognitive-os/skill_store.db`` at 0 bytes since
2026-05-06.

The shape below is transcribed from 285 real Agent tool calls and 266 real
results in ``~/.claude/projects/-Users-...-luum-agent-os/*.jsonl``:

    tool_input   : description, subagent_type, model, prompt, run_in_background
    tool_response: status, agentId, isAsync, description, resolvedModel, prompt,
                   outputFile, canReadOutputFile  (+ agentType, content,
                   totalDurationMs, totalTokens, totalToolUseCount, usage,
                   toolStats on the 6/266 synchronous completions)
    status values: async_launched (260) | completed (6)

Do NOT re-derive this payload from the hook's own parser — that makes the test
follow the hook's assumptions instead of the harness's, which is the exact bug
this suite failed to catch.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sqlite3
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "skill-post-execution-analysis.sh"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _make_payload(
    subagent_type: str = "test-hook-skill",
    status: str = "completed",
    tool_count: int = 2,
    duration_ms: int = 500,
    session_id: str = "test-session-001",
    *,
    with_agent_type: bool = True,
) -> dict:
    """Build a PostToolUse Agent payload in the shape the harness really sends.

    Field names come from the transcripts (see module docstring), not from the
    hook: ``totalToolUseCount`` / ``totalDurationMs`` / ``agentType``, never
    ``tool_count`` / ``duration_ms`` / ``skill_name``.
    """
    tool_response = {
        "status": status,
        "agentId": "a" * 17,
        "isAsync": False,
        "description": "test agent run",
        "resolvedModel": "claude-sonnet-4-5",
        "prompt": "do the thing",
        "outputFile": "/tmp/agent-output.jsonl",
        "canReadOutputFile": True,
        "content": [{"type": "text", "text": "done"}],
        "totalDurationMs": duration_ms,
        "totalTokens": 1234,
        "totalToolUseCount": tool_count,
    }
    if with_agent_type:
        tool_response["agentType"] = subagent_type
    return {
        "session_id": session_id,
        "transcript_path": "/tmp/transcript.jsonl",
        "cwd": "/tmp",
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {
            "description": "test agent run",
            "subagent_type": subagent_type,
            "model": "sonnet",
            "prompt": "do the thing",
        },
        "tool_response": tool_response,
    }


def _run_hook(
    payload: dict,
    tmp_path: Path,
    *,
    env_overrides: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run the hook with synthetic payload via stdin."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        # Override DB path to tmp
        "_HOOK_PAYLOAD": json.dumps(payload),
    }
    if env_overrides:
        env.update(env_overrides)

    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Helpers to set up tmp project structure
# ---------------------------------------------------------------------------


def _setup_tmp_project(tmp_path: Path) -> Path:
    """Create minimal .cognitive-os dir in tmp_path."""
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


class TestHookBasicExecution:
    def test_hook_exits_zero_on_valid_payload(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload()
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0, f"Hook stderr: {result.stderr}"

    def test_hook_exits_zero_on_empty_payload(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)},
            timeout=10,
        )
        assert result.returncode == 0

    def test_killswitch_exits_immediately(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload()
        result = _run_hook(
            payload,
            tmp_path,
            env_overrides={"DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS": "1"},
        )
        assert result.returncode == 0
        # With killswitch, no DB should be created
        db = tmp_path / ".cognitive-os" / "skill_store.db"
        assert not db.exists(), "Killswitch should prevent DB writes"

    def test_no_skill_name_exits_zero(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        # Real Agent payload with every name-bearing field stripped: the hook
        # must degrade to exit 0 rather than write a nameless record.
        payload = _make_payload(with_agent_type=False)
        payload["tool_input"].pop("subagent_type")
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0
        assert not (tmp_path / ".cognitive-os" / "skill_store.db").exists()


# ---------------------------------------------------------------------------
# SkillStore write
# ---------------------------------------------------------------------------


class TestSkillStoreWrite:
    def test_writes_skill_record_to_db(self, tmp_path: Path) -> None:
        _setup_tmp_project(tmp_path)
        payload = _make_payload("write-test-skill")
        result = _run_hook(payload, tmp_path)
        assert result.returncode == 0

        db_path = tmp_path / ".cognitive-os" / "skill_store.db"
        assert db_path.exists(), "SkillStore DB should be created for valid skill execution"

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT name FROM skill_records WHERE skill_id=?",
            (_sha("write-test-skill"),),
        ).fetchone()
        conn.close()
        assert row is not None, "Expected skill_records row"
        assert row[0] == "write-test-skill"


# ---------------------------------------------------------------------------
# Discipline gate: propose-only artifact
# ---------------------------------------------------------------------------


class TestDisciplineGate:
    """Only the structural gate survives.

    DELETED 2026-08-19 — test_candidate_writes_proposal_file,
    test_non_candidate_does_not_write_proposal and
    test_proposal_contains_discipline_gate_marker. All three drove the
    ``candidate_for_evolution`` heuristic, which fires on ``len(tool_issues)>=3``
    or ``status in (error|fail|failed|1) and duration>30s``. The harness sends
    no ``tool_issues`` field at all, and the only two ``status`` values it ever
    emits for Agent are ``async_launched`` (260/266) and ``completed`` (6/266).
    The heuristic is therefore unreachable in production, and the three tests
    proved only that the hook agrees with its own invented payload. They also
    carried a dead assertion (``assert ... or True``). Re-add real coverage when
    ADR-176's candidate heuristic is redefined against fields the harness
    actually sends; do not re-add it against fabricated ones.
    """

    def test_no_live_skill_md_write_path_exists(self) -> None:
        """Structural: grep the hook for any write path to SKILL.md.

        This is the DISCIPLINE GATE code-path test (ADR-176 AC #10).
        A write to live SKILL.md from the hook would be a violation.
        """
        hook_content = HOOK.read_text()
        # Check executable lines only; comments may document the forbidden path.
        executable = "\n".join(
            line for line in hook_content.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        # The hook must never contain a write path like "tee .../SKILL.md" or "> SKILL.md".
        forbidden_patterns = [
            r"SKILL\.md\s*>",
            r">\s*[^\n]*SKILL\.md",
            r"tee\s+[^\n]*SKILL\.md",
            r"cat\s+[^\n]*>\s*[^\n]*SKILL",
            r"Path\([^\n]*SKILL\.md[^\n]*\)\.write_text",
        ]
        import re
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, executable)
            assert not matches, (
                f"DISCIPLINE GATE VIOLATION: Hook contains live SKILL.md mutation "
                f"matching pattern '{pattern}': {matches}"
            )


# ---------------------------------------------------------------------------
# Latency budget (soft)
# ---------------------------------------------------------------------------


class TestLatencyBudget:
    def test_hook_completes_within_200ms(self, tmp_path: Path) -> None:
        """Soft latency check: hook should complete in <200ms on a simple payload.

        This is advisory — CI machines may be slower; we allow 5x headroom.
        """
        _setup_tmp_project(tmp_path)
        payload = _make_payload("latency-skill")
        start = time.monotonic()
        result = _run_hook(payload, tmp_path)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.returncode == 0
        # 1000ms = 5x the 200ms budget; accounts for subprocess + CI overhead
        assert elapsed_ms < 1000, (
            f"Hook took {elapsed_ms:.0f}ms — exceeded 1000ms soft limit "
            f"(ADR-176 budget is 200ms). stderr: {result.stderr[:200]}"
        )
