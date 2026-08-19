# SCOPE: os-only
"""Behavioural test for the post-execution skill analysis hook (ADR-176).

The hook asked the payload for a `skill_name` that no payload of this harness
carries, bailed at `if [ -z "$SKILL_NAME" ]`, and so wrote nothing: 182 recorded
invocations and `.cognitive-os/skill_store.db` at exactly 0 bytes since
2026-05-06.

What the harness DOES send on PostToolUse for the Agent tool — shape confirmed
over 226 real Agent results in the `~/.claude/projects` transcripts
(2026-08-19) — is `tool_response` as an object with `agentType`, `status`,
`content`, `totalDurationMs`, `totalTokens` and `totalToolUseCount`. The Skill
tool carries its name at `tool_input.skill`, the same field
`hooks/skill-usage-tracker.sh` reads.

Covered in both directions:
  * a real Agent payload MUST land one row in `skill_execution_events`, with the
    tool count and duration taken from the fields the harness really sends;
  * a failed Agent call (whose `tool_response` is the "Error: ..." STRING shape)
    MUST still be recorded, identified from `tool_input.subagent_type`;
  * a Skill-tool payload MUST be recorded under its skill name;
  * a payload with nothing that identifies a skill MUST write no database at
    all, and a Bash payload must not even reach the Python path;
  * the discipline gate (ADR-133/134) MUST NOT write into any live SKILL.md.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_REL = "hooks/skill-post-execution-analysis.sh"
DB_REL = ".cognitive-os/skill_store.db"


def _hook_source() -> Path:
    """Where to copy the hook from — overridable only for the falsification run."""
    override = os.environ.get("COS_TEST_HOOK_SOURCE_DIR")
    base = Path(override) if override else REPO_ROOT
    return base / HOOK_REL


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    repo = (tmp_path / "repo").resolve()
    (repo / "hooks").mkdir(parents=True)
    shutil.copy(_hook_source(), repo / HOOK_REL)
    (repo / HOOK_REL).chmod(0o755)
    (repo / ".cognitive-os" / "metrics").mkdir(parents=True)
    return repo


def agent_payload(
    agent_type: str = "Explore",
    status: str = "completed",
    tool_uses: int = 9,
    duration_ms: int = 41230,
) -> dict:
    return {
        "tool_name": "Agent",
        "tool_input": {"description": "sweep the hooks", "subagent_type": agent_type},
        "tool_response": {
            "status": status,
            "agentType": agent_type,
            "content": [{"type": "text", "text": "swept 154 hooks"}],
            "totalDurationMs": duration_ms,
            "totalTokens": 18422,
            "totalToolUseCount": tool_uses,
        },
        "session_id": "sess-abc",
    }


def run_hook(repo: Path, payload: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env["COS_SOURCE_ROOT"] = str(REPO_ROOT)
    env.pop("_HOOK_PAYLOAD", None)
    env.pop("DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS", None)
    return subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=120,
    )


def execution_rows(repo: Path) -> list[tuple]:
    db = repo / DB_REL
    if not db.exists() or db.stat().st_size == 0:
        return []
    conn = sqlite3.connect(str(db))
    try:
        return conn.execute(
            "SELECT name, status, tool_count, duration_ms, agent_session_id "
            "FROM skill_execution_events ORDER BY id"
        ).fetchall()
    finally:
        conn.close()


# --- must record -------------------------------------------------------------


def test_real_agent_payload_is_recorded(repo: Path) -> None:
    """182 invocations wrote a 0-byte database because of the field this asserts."""
    result = run_hook(repo, agent_payload())

    assert result.returncode == 0, result.stderr
    rows = execution_rows(repo)
    assert rows, "nothing was recorded for a real Claude Code Agent payload"
    name, status, tool_count, duration_ms, session = rows[-1]
    assert name == "Explore"
    assert status == "completed"
    assert tool_count == 9, "tool count did not come from totalToolUseCount"
    assert duration_ms == 41230, "duration did not come from totalDurationMs"
    assert session == "sess-abc"


def test_failed_agent_call_is_still_recorded(repo: Path) -> None:
    """On failure the harness sends `tool_response` as an 'Error: ...' STRING.

    The agent identity then only survives in `tool_input.subagent_type`.
    """
    payload = {
        "tool_name": "Agent",
        "tool_input": {"description": "sweep the hooks", "subagent_type": "Plan"},
        "tool_response": "Error: Exit code 1",
        "session_id": "sess-fail",
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    rows = execution_rows(repo)
    assert rows, "a failed agent call left no trace at all"
    assert rows[-1][0] == "Plan"


def test_skill_tool_payload_is_recorded(repo: Path) -> None:
    payload = {
        "tool_name": "Skill",
        "tool_input": {"skill": "systematic-debugging"},
        "tool_response": {"status": "completed", "content": [{"type": "text", "text": "ok"}]},
        "session_id": "sess-skill",
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    rows = execution_rows(repo)
    assert rows and rows[-1][0] == "systematic-debugging"


def test_repeated_executions_accumulate(repo: Path) -> None:
    run_hook(repo, agent_payload(agent_type="Explore"))
    run_hook(repo, agent_payload(agent_type="Plan"))

    names = [row[0] for row in execution_rows(repo)]
    assert names == ["Explore", "Plan"], names


# --- must stay out of the way ------------------------------------------------


def test_payload_without_any_skill_identity_writes_nothing(repo: Path) -> None:
    payload = {
        "tool_name": "Agent",
        "tool_input": {"description": "sweep the hooks"},
        "tool_response": {"status": "completed", "content": []},
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    assert execution_rows(repo) == [], "invented a skill identity that the payload never carried"


def test_bash_payload_is_ignored(repo: Path) -> None:
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "git status"},
        "tool_response": {"stdout": "", "stderr": "", "interrupted": False},
    }
    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    assert execution_rows(repo) == []


def test_killswitch_stops_the_hook(repo: Path) -> None:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(repo)
    env["COS_SOURCE_ROOT"] = str(REPO_ROOT)
    env["DISABLE_HOOK_SKILL_POST_EXECUTION_ANALYSIS"] = "1"
    result = subprocess.run(
        ["/bin/bash", str(repo / HOOK_REL)],
        input=json.dumps(agent_payload()),
        text=True,
        capture_output=True,
        env=env,
        cwd=str(repo),
        timeout=120,
    )

    assert result.returncode == 0, result.stderr
    assert execution_rows(repo) == []


def test_discipline_gate_writes_only_proposals(repo: Path) -> None:
    """ADR-133/134: no write path to a live SKILL.md, only to the proposals dir."""
    payload = agent_payload()
    payload["tool_response"]["tool_issues"] = ["a", "b", "c"]

    result = run_hook(repo, payload)

    assert result.returncode == 0, result.stderr
    proposals = list((repo / "docs" / "06-Daily" / "reports" / "skill-analysis-proposals").rglob("*.md"))
    assert proposals, "a flagged execution produced no propose-only artifact"
    assert "propose_only" in proposals[0].read_text(encoding="utf-8")
    assert not list(repo.rglob("SKILL.md")), "the hook wrote into a live skill file"


@pytest.mark.parametrize("status", ["completed", "error"])
def test_hook_never_blocks(repo: Path, status: str) -> None:
    result = run_hook(repo, agent_payload(status=status))
    assert result.returncode == 0, result.stderr
