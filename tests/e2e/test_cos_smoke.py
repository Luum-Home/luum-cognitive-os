"""E2E Smoke Suite — Critical path of the Cognitive OS.

Steps exercised:
  1. session-init.sh + session-start-worktree-nudge.sh (hooks fire, exit 0)
  2. rate-limit-precheck.sh with a fake bash command (additionalContext field)
  3. lib.rate_limiter.RateLimitQueue.enqueue() + dequeue_ready (JSONL events)
  4. lib.harness_adapter.dispatch.dispatch_event with fake CC Pre event
     (canonical event written to metrics/)
  5. scripts/cos_sprint.py run <fixture.yaml> (manifest created)
  6. lib.self_knowledge.query("rate limiter") returns a list

Each step is isolated via tmp_path; no global state leaks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _repo(rel: str) -> Path:
    return _REPO_ROOT / rel


def _make_cos_layout(base: Path) -> Path:
    """Create minimal .cognitive-os/ structure under *base*."""
    cos = base / ".cognitive-os"
    for sub in ("metrics", "sessions", "sprints", "self-knowledge"):
        (cos / sub).mkdir(parents=True, exist_ok=True)
    # Minimal cognitive-os.yaml so lib.paths / lib.rate_limiter can find project root
    (base / "cognitive-os.yaml").write_text(
        "project:\n  phase: reconstruction\n  name: smoke-test\n",
        encoding="utf-8",
    )
    return cos


def _run_hook(hook_name: str, env: Dict[str, str], stdin_json: str = "") -> subprocess.CompletedProcess:
    """Execute a hook script and return CompletedProcess."""
    hook_path = _repo(f"hooks/{hook_name}")
    result = subprocess.run(
        ["bash", str(hook_path)],
        input=stdin_json,
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, **env},
    )
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Temp project directory with minimal .cognitive-os/ layout."""
    _make_cos_layout(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Step 1 — Session hooks
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step1_session_hooks(project_dir: Path) -> None:
    """session-init.sh and session-start-worktree-nudge.sh must exit 0."""
    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        # Prevent hooks from hanging on missing git config
        "HOME": str(project_dir),
    }

    # session-init.sh
    result = _run_hook("session-init.sh", env=env)
    assert result.returncode == 0, (
        f"session-init.sh failed (exit {result.returncode}):\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )

    # At least one session directory should have been created
    sessions_dir = project_dir / ".cognitive-os" / "sessions"
    session_dirs = [d for d in sessions_dir.iterdir() if d.is_dir() and d.name not in ("locks",)]
    assert len(session_dirs) >= 1, "session-init.sh should create a session directory"

    # session-start-worktree-nudge.sh
    result2 = _run_hook("session-start-worktree-nudge.sh", env=env)
    assert result2.returncode == 0, (
        f"session-start-worktree-nudge.sh failed (exit {result2.returncode}):\n"
        f"stdout: {result2.stdout[:500]}\nstderr: {result2.stderr[:500]}"
    )


# ---------------------------------------------------------------------------
# Step 2 — rate-limit-precheck.sh
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step2_rate_limit_precheck(project_dir: Path) -> None:
    """rate-limit-precheck.sh must exit 0 and produce no blocking output."""
    # The hook expects a JSON payload on stdin (PreToolUse:Bash format)
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "echo smoke_test_command_12345"},
        "tool_use_id": "smoke-tu-001",
        "session_id": "smoke-session-001",
    })

    env = {
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "HOME": str(project_dir),
    }

    result = _run_hook("rate-limit-precheck.sh", env=env, stdin_json=payload)

    # Must never block a tool call
    assert result.returncode == 0, (
        f"rate-limit-precheck.sh exited {result.returncode}:\n"
        f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
    )

    # The hook either outputs nothing (no match) or outputs additionalContext JSON
    stdout = result.stdout.strip()
    if stdout:
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            # Partial output is allowed — hook may have printed debug lines
            pass
        else:
            # If JSON was emitted, it must follow the additionalContext contract
            assert isinstance(data, dict), "stdout JSON must be a dict"


# ---------------------------------------------------------------------------
# Step 3 — RateLimitQueue enqueue + dequeue_ready
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step3_rate_limit_queue(project_dir: Path) -> None:
    """enqueue() writes a JSONL event; dequeue_ready() returns queued items."""
    sys.path.insert(0, str(_REPO_ROOT))
    from lib.rate_limiter import RateLimitQueue  # noqa: PLC0415

    queue_path = str(project_dir / ".cognitive-os" / "rate-limit-queue.json")
    queue = RateLimitQueue(
        state_path=queue_path,
        cooldown_seconds=0,  # immediately eligible
    )

    # Enqueue an action
    qid = queue.enqueue(
        "agent_launch",
        context={"description": "smoke test agent", "model": "sonnet"},
    )
    assert qid, "enqueue() must return a non-empty queue_id"

    # JSONL events file should exist and contain a 'queued' event
    jsonl_path = Path(queue_path + "l")  # .json -> .jsonl
    assert jsonl_path.exists(), f"JSONL event log not created at {jsonl_path}"

    events = [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]
    actions = [e.get("action") for e in events]
    assert "queued" in actions, f"Expected 'queued' event in JSONL, got: {actions}"

    # dequeue_ready returns items (cooldown=0, so immediately eligible)
    ready = queue.dequeue_ready()
    assert isinstance(ready, list), "dequeue_ready() must return a list"
    assert len(ready) >= 1, "At least one item should be dequeue-ready (cooldown=0)"
    assert ready[0].get("action_type") == "agent_launch"


# ---------------------------------------------------------------------------
# Step 4 — harness_adapter.dispatch.dispatch_event (canonical event)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step4_canonical_event_emission(project_dir: Path) -> None:
    """dispatch_event with a fake CC PreToolUse:Agent payload emits a canonical event."""
    sys.path.insert(0, str(_REPO_ROOT))
    from lib.harness_adapter.dispatch import dispatch_event  # noqa: PLC0415

    fake_pre_event: Dict[str, Any] = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_use_id": "smoke-tu-agent-001",
        "tool_input": {
            "description": "Smoke test agent task",
            "prompt": "do something",
        },
        "session_id": "smoke-session-001",
    }

    result = dispatch_event(
        fake_pre_event,
        project_dir=project_dir,
    )

    assert result["harness"] != "none", (
        f"No adapter matched the fake event. harness='{result['harness']}'"
    )
    assert len(result["events"]) >= 1, (
        f"Expected at least 1 canonical event, got 0. result={result}"
    )

    # Canonical event should have been written to a JSONL file
    output_path = result.get("output_path")
    assert output_path is not None, "dispatch_event must return an output_path"

    written = Path(output_path)
    assert written.exists(), f"Canonical output file not created: {output_path}"

    lines = [l for l in written.read_text().splitlines() if l.strip()]
    assert len(lines) >= 1, "At least one canonical event must be written to JSONL"

    emitted = json.loads(lines[-1])
    assert "event_type" in emitted, "Canonical event must have 'event_type' field"


# ---------------------------------------------------------------------------
# Step 5 — cos_sprint.py run
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step5_sprint_cli_run(project_dir: Path) -> None:
    """cos_sprint.py run <fixture.yaml> creates a manifest."""
    fixture = _repo("tests/fixtures/e2e/sprint-smoke.yaml")
    assert fixture.exists(), f"Sprint fixture not found: {fixture}"

    sprint_script = _repo("scripts/cos_sprint.py")
    assert sprint_script.exists(), f"cos_sprint.py not found: {sprint_script}"

    result = subprocess.run(
        [sys.executable, str(sprint_script), "run", str(fixture)],
        capture_output=True,
        text=True,
        timeout=20,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "PYTHONPATH": str(_REPO_ROOT),
        },
    )

    assert result.returncode == 0, (
        f"cos_sprint.py run exited {result.returncode}:\n"
        f"stdout: {result.stdout[:800]}\nstderr: {result.stderr[:800]}"
    )

    # Manifest directory should contain a .json file
    sprints_dir = project_dir / ".cognitive-os" / "sprints"
    manifest_files = list(sprints_dir.glob("*.json"))
    assert len(manifest_files) >= 1, (
        f"No sprint manifests created under {sprints_dir}"
    )

    # Manifest must be valid JSON with expected fields
    manifest = json.loads(manifest_files[0].read_text())
    assert manifest.get("name") == "smoke-sprint", (
        f"Manifest name mismatch: {manifest.get('name')}"
    )
    assert len(manifest.get("tasks", [])) == 2, (
        f"Expected 2 tasks, got {len(manifest.get('tasks', []))}"
    )

    # cos_sprint.py list should also succeed
    result2 = subprocess.run(
        [sys.executable, str(sprint_script), "list"],
        capture_output=True,
        text=True,
        timeout=10,
        env={
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "PYTHONPATH": str(_REPO_ROOT),
        },
    )
    assert result2.returncode == 0, (
        f"cos_sprint.py list failed: {result2.stderr[:400]}"
    )
    # Output should reference our sprint name
    assert "smoke-sprint" in result2.stdout, (
        f"'smoke-sprint' not found in list output:\n{result2.stdout[:400]}"
    )


# ---------------------------------------------------------------------------
# Step 6 — lib.self_knowledge.query
# ---------------------------------------------------------------------------


@pytest.mark.e2e
@pytest.mark.timeout(30)
def test_step6_self_knowledge_query(project_dir: Path) -> None:
    """self_knowledge.query('rate limiter') returns a list.

    The self-knowledge index may or may not be built in CI.  We accept:
    - A non-empty list (index present, matches found): ideal.
    - An empty list (index present but no match, or index not built): acceptable.

    We only FAIL if the function raises an exception.
    """
    sys.path.insert(0, str(_REPO_ROOT))
    from lib import self_knowledge  # noqa: PLC0415

    # Point at the real project index (not the temp dir — index lives in the repo)
    try:
        results = self_knowledge.query("rate limiter", project_dir=_REPO_ROOT)
    except FileNotFoundError:
        # Index not built in this environment — that is acceptable for the smoke
        # test.  The important thing is the function is importable and callable.
        pytest.skip("self-knowledge index not built (run cos_build_self_knowledge.py)")

    assert isinstance(results, list), (
        f"query() must return a list, got {type(results)}"
    )
    # Each result must have the expected schema
    for item in results:
        assert "source" in item, f"Result missing 'source': {item}"
        assert "key" in item, f"Result missing 'key': {item}"
        assert "score" in item, f"Result missing 'score': {item}"
