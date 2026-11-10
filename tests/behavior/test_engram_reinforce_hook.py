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

``reinforce()`` talks to the engram HTTP API (GET /health, GET and PATCH
/observations/<id>) at ``ENGRAM_HTTP_URL``, which defaults to the user's daemon
on 127.0.0.1:7437. Every hook run here gets ``ENGRAM_HTTP_URL`` pointed at an
in-process double on an ephemeral port that answers /health and 404s every
observation, so the suite never depends on, nor reaches, the user's daemon,
and the path it exercises is the same whether that daemon is up or not. The
double records each request, which lets the tests assert the hook only reads.
"""

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

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

USER_ENGRAM_PORT = 7437


class _EngramDouble(BaseHTTPRequestHandler):
    """Engram HTTP API double: /health is up, every observation is a 404."""

    def _answer(self) -> None:
        self.server.requests.append((self.command, self.path))
        status = 200 if self.path == "/health" else 404
        body = b'{"status":"ok"}' if status == 200 else b'{"error":"not found"}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_PATCH = do_POST = do_PUT = do_DELETE = _answer

    def log_message(self, *args) -> None:
        pass


@pytest.fixture
def engram_http_double():
    """A private engram HTTP double on an ephemeral loopback port.

    Yields ``(base_url, requests)``; ``requests`` collects ``(method, path)``.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _EngramDouble)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", server.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


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
    engram_http_url: str,
    *,
    env_var: str = "COGNITIVE_OS_PROJECT_DIR",
) -> "subprocess.CompletedProcess[str]":
    port = urlparse(engram_http_url).port
    if port in (None, USER_ENGRAM_PORT):
        pytest.fail(f"the hook must not reach the user's engram daemon: {engram_http_url!r}")
    env = os.environ.copy()
    env.pop("COGNITIVE_OS_PROJECT_DIR", None)
    env.pop("CODEX_PROJECT_DIR", None)
    env.pop("CLAUDE_PROJECT_DIR", None)
    env[env_var] = str(project_dir)
    env["ENGRAM_HTTP_URL"] = engram_http_url
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


def test_reinforce_hook_logs_one_row_per_retrieval_carrying_every_id(tmp_path, engram_http_double):
    """A search that returned two observations is ONE row listing both ids."""
    engram_url, engram_requests = engram_http_double
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_search", SEARCH_RESULT),
        engram_url,
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
    # Reinforcement went to the double, read only, and stopped at the 404s.
    assert engram_requests == [
        ("GET", "/health"),
        ("GET", "/observations/99000123"),
        ("GET", "/health"),
        ("GET", "/observations/99000456"),
    ]


def test_reinforce_hook_records_a_stated_miss_as_a_miss(tmp_path, engram_http_double):
    """"No memories found" is a real negative: memory was consulted and empty.

    It is not the same as "no row", which is what an unreadable payload gets.
    """
    engram_url, engram_requests = engram_http_double
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_search", MISS_RESULT),
        engram_url,
    )

    assert result.returncode == 0, result.stderr
    rows = _rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["outcome"] == "miss"
    assert rows[0]["observation_ids"] == []
    assert rows[0]["n"] == 0
    assert engram_requests == [], "a miss has nothing to reinforce"


def test_reinforce_hook_ignores_unrelated_tool_events(tmp_path, engram_http_double):
    """mem_save is a write, not a retrieval — nothing to reinforce, no row."""
    engram_url, engram_requests = engram_http_double
    result = _run_hook(
        tmp_path,
        _mcp_payload("mcp__plugin_engram_engram__mem_save", "Saved observation #99000123."),
        engram_url,
    )

    assert result.returncode == 0, result.stderr
    assert not _ledger(tmp_path).exists()
    assert engram_requests == []


def test_reinforce_hook_writes_under_codex_project_dir(tmp_path, engram_http_double):
    """CODEX_PROJECT_DIR resolves the ledger root when the Claude var is absent."""
    engram_url, engram_requests = engram_http_double
    result = _run_hook(
        tmp_path,
        _mcp_payload(
            "mcp__plugin_engram_engram__mem_get_observation", GET_OBSERVATION_RESULT
        ),
        engram_url,
        env_var="CODEX_PROJECT_DIR",
    )

    assert result.returncode == 0, result.stderr
    rows = _rows(tmp_path)
    assert rows[-1]["observation_ids"] == ["99000789"]
    assert rows[-1]["tool"] == "mem_get_observation"
    assert engram_requests == [("GET", "/health"), ("GET", "/observations/99000789")]


def test_reinforce_hook_treats_the_old_phantom_field_as_drift(tmp_path, engram_http_double):
    """The regression guard for the bug this hook was rewritten to fix.

    A payload carrying the result under ``tool_result`` — the field the harness
    never sends and the old hook read — must produce NO ledger row and a
    payload-contract-drift row. Reading absence as "nothing to reinforce" is
    exactly how the ledger stayed empty for three months.
    """
    engram_url, engram_requests = engram_http_double
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
        engram_url,
    )

    assert result.returncode == 0, result.stderr
    assert not _ledger(tmp_path).exists(), (
        "an unreadable payload must never be counted as a retrieval"
    )

    drift = tmp_path / ".cognitive-os" / "metrics" / "payload-contract-drift.jsonl"
    assert drift.exists(), "a payload we cannot read is an alarm, not a silent no-op"
    row = json.loads(drift.read_text().splitlines()[-1])
    assert row["hook"] == "engram-reinforce-on-access.sh"
    assert engram_requests == []
