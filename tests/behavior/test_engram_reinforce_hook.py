"""Behavior tests for the Engram access-reinforcement hook.

WHAT THESE TESTS SEND, AND WHY IT CHANGED (2026-08-16)
------------------------------------------------------
They used to build ``{"tool_result": {"observations": [{"id": 123}, ...]}}``
and assert one ledger row per id, carrying a scalar ``observation_id``.

Every part of that was the defect the hook was rewritten to remove:

* ``tool_result`` is a PHANTOM. The PostToolUse payload carries the result under
  ``tool_response`` — the same field ``hooks/_lib/tool-outcome.sh`` documents and
  ``tests/fixtures/payload-corpus/harness-payloads.jsonl`` freezes. Reading the
  phantom is what kept ``lifecycle-reinforcement.jsonl`` from ever existing.
* ``{"observations": [{"id": ...}]}`` is a shape no MCP server sends. A real MCP
  tool response is an ARRAY of content blocks —
  ``[{"type": "text", "text": "<json string>"}]`` — whose inner JSON is
  ``{project, project_path, project_source, result}``, and ``result`` is PROSE
  with the ids written as ``#<digits>``. Corpus record:
  ``{"_corpus": {"tool": "mcp__plugin_engram_engram__mem_search", "state": "list"},
  "toolUseResult": [{"text": "<str>", "type": "<str>"}]}``.
* One row per id was never the ledger contract either. A row is one OBSERVED
  RETRIEVAL: ``{tool, outcome, observation_ids[], n, project}``. That is what
  ``scripts/check_memory_retrieval_arrival.py`` reads back
  (``r.get("observation_ids")``), so a per-id row would corroborate nothing.

The prose forms below are the two the hook anchors on, and the same two
``_ID_PATTERNS`` in ``scripts/check_memory_retrieval_arrival.py`` match.

Observation ids here are deliberately out of range (``99000…``). ``reinforce()``
talks to the engram HTTP daemon on port 7437 when one is running; an id that
cannot exist makes the GET a 404 and guarantees these tests never PATCH a real
observation.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "engram-reinforce-on-access.sh"

SEARCH_RESULT = """Found 2 memories in project luum-agent-os:

[1] #99000123 (manual) — Decidir el contrato de salida de los hooks
    2026-08-15 · confidence 0.62
[2] #99000456 (manual) — Reescribir engram-reinforce-on-access
    2026-08-15 · confidence 0.51
"""

GET_OBSERVATION_RESULT = """#99000789 [manual] Reinforcement ledger contract
Saved 2026-08-15 in project luum-agent-os.

The row is one retrieval, not one id.
"""

MISS_RESULT = "No memories found for that query in project luum-agent-os."


def _mcp_payload(tool_name: str, result: str, project: str = "luum-agent-os") -> dict:
    """A PostToolUse payload in the shape an MCP server actually returns."""
    return {
        "tool_name": tool_name,
        "tool_response": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "project": project,
                        # Present in the real payload and deliberately never
                        # stored: it embeds the operator's home directory.
                        "project_path": "/home/<redacted>/projects/luum-agent-os",
                        "project_source": "cwd",
                        "result": result,
                    }
                ),
            }
        ],
    }


def _run_hook(
    project_dir: Path,
    payload: dict,
    *,
    env_var: str = "COGNITIVE_OS_PROJECT_DIR",
) -> "subprocess.CompletedProcess[str]":
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env[env_var] = str(project_dir)
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
        env=env,
        timeout=10,
    )


def _ledger(project_dir: Path) -> Path:
    return project_dir / ".cognitive-os" / "metrics" / "lifecycle-reinforcement.jsonl"


def _rows(project_dir: Path) -> list:
    path = _ledger(project_dir)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_reinforce_hook_logs_one_row_per_retrieval_carrying_every_id(tmp_path):
    """A search that returned two observations is ONE row listing both ids."""
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_search", SEARCH_RESULT),
    )

    assert result.returncode == 0, result.stderr
    rows = _rows(tmp_path)
    assert len(rows) == 1, f"one retrieval must be one row, got {len(rows)}"
    assert rows[0]["observation_ids"] == ["99000123", "99000456"]
    assert rows[0]["n"] == 2
    assert rows[0]["tool"] == "mem_search"
    assert rows[0]["outcome"] == "hit"
    assert rows[0]["project"] == "luum-agent-os"
    assert "project_path" not in rows[0], (
        "project_path embeds the operator's home and must never reach the ledger"
    )


def test_reinforce_hook_records_a_stated_miss_as_a_miss(tmp_path):
    """"No memories found" is a real negative: memory was consulted and empty.

    It is not the same as "no row", which is what an unreadable payload gets.
    """
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_search", MISS_RESULT),
    )

    assert result.returncode == 0, result.stderr
    rows = _rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "miss"
    assert rows[0]["observation_ids"] == []
    assert rows[0]["n"] == 0


def test_reinforce_hook_ignores_unrelated_tool_events(tmp_path):
    """mem_save is a write, not a retrieval — nothing to reinforce, no row."""
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_save", "Saved observation #99000123."),
    )

    assert result.returncode == 0, result.stderr
    assert not _ledger(tmp_path).exists()


def test_reinforce_hook_writes_under_codex_project_dir(tmp_path):
    """CODEX_PROJECT_DIR resolves the ledger root when the Claude var is absent."""
    result = _run_hook(
        tmp_path,
        _mcp_payload(
            "mcp__plugin_engram_engram__mem_get_observation", GET_OBSERVATION_RESULT
        ),
        env_var="CODEX_PROJECT_DIR",
    )

    assert result.returncode == 0, result.stderr
    rows = _rows(tmp_path)
    assert rows[-1]["observation_ids"] == ["99000789"]
    assert rows[-1]["tool"] == "mem_get_observation"


def test_reinforce_hook_treats_the_old_phantom_field_as_drift(tmp_path):
    """The regression guard for the bug this hook was rewritten to fix.

    A payload carrying the result under ``tool_result`` — the field the harness
    never sends and the old hook read — must produce NO ledger row and a
    payload-contract-drift row. Reading absence as "nothing to reinforce" is
    exactly how the ledger stayed empty for three months.
    """
    # The drift recorder lives in the project's own hooks/_lib, which the hook
    # sources from PROJECT_ROOT; tmp_path needs a copy for the recorder to exist.
    lib = tmp_path / "hooks" / "_lib"
    lib.mkdir(parents=True)
    for name in ("tool-outcome.sh", "safe-jsonl.sh"):
        shutil.copy(REPO_ROOT / "hooks" / "_lib" / name, lib / name)

    result = _run_hook(
        tmp_path,
        {
            "tool_name": "mcp__plugin_engram_engram__mem_search",
            "tool_result": {"observations": [{"id": 99000123}]},
        },
    )

    assert result.returncode == 0, result.stderr
    assert not _ledger(tmp_path).exists(), (
        "an unreadable payload must never be counted as a retrieval"
    )

    drift = tmp_path / ".cognitive-os" / "metrics" / "payload-contract-drift.jsonl"
    assert drift.exists(), "a payload we cannot read is an alarm, not a silent no-op"
    row = json.loads(drift.read_text().splitlines()[-1])
    assert row["hook"] == "engram-reinforce-on-access.sh"
