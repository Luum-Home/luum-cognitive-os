"""Post-Bash dispatch queue tick coverage.

The dispatch gate can enqueue Agent intents while a validation capsule or
capacity gate is active. When a later Bash command frees the gate, there must
be a cheap PostToolUse tick that calls QueueDrainer and surfaces ready work.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "hooks" / "rate-limit-drain.sh"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_project(tmp_path: Path, *, active_tasks: int = 0) -> None:
    (tmp_path / "cognitive-os.yaml").write_text(
        "max_parallel_agents: 2\nproject:\n  phase: reconstruction\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / ".cognitive-os" / "tasks" / "active-tasks.json",
        {
            "version": 1,
            "tasks": [
                {"id": f"active-{idx}", "status": "in_progress"}
                for idx in range(active_tasks)
            ],
        },
    )
    _write_json(
        tmp_path / ".cognitive-os" / "tasks" / "dispatch-queue.json",
        [
            {
                "id": "queued-agent-1",
                "prompt": "Review the queue-drain gap",
                "description": "Review queue-drain gap",
                "model": "sonnet",
                "priority": 5,
                "enqueued_at": "2026-05-20T00:00:00Z",
                "status": "queued",
                "_enqueued_epoch": time.time(),
                "_fingerprint": "queue-drain-gap",
            }
        ],
    )


def _run_hook(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO),
        # Keep the rate-limit side quiet; this test targets the dispatch tick.
        "COGNITIVE_OS_DISABLE_PRIVATE_MODE": "1",
    }
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )


def test_post_bash_tick_surfaces_ready_dispatch_queue_without_mutating_status(tmp_path: Path) -> None:
    _seed_project(tmp_path, active_tasks=0)

    result = _run_hook(tmp_path)

    assert result.returncode == 0
    assert "DISPATCH_QUEUE_READY: 1 queued Agent intent(s) ready to launch" in result.stderr
    assert "queue_id=queued-agent-1" in result.stderr

    queue = json.loads(
        (tmp_path / ".cognitive-os" / "tasks" / "dispatch-queue.json").read_text(
            encoding="utf-8"
        )
    )
    assert queue[0]["status"] == "queued"


def test_post_bash_tick_stays_quiet_when_validation_capsule_is_active(tmp_path: Path) -> None:
    _seed_project(tmp_path, active_tasks=0)
    capsule_dir = tmp_path / ".cognitive-os" / "runtime" / "active-capsule"
    capsule_dir.mkdir(parents=True)
    now = int(time.time())
    _write_json(
        tmp_path / ".cognitive-os" / "runtime" / "validation-capsule.lock",
        {
            "pid": os.getpid(),
            "started_at_epoch": now,
            "expires_at_epoch": now + 3600,
            "last_heartbeat_epoch": now,
            "heartbeat_interval_seconds": 30,
            "capsule_dir": str(capsule_dir),
        },
    )

    result = _run_hook(tmp_path)

    assert result.returncode == 0
    assert "DISPATCH_QUEUE_READY" not in result.stderr


def test_post_bash_tick_ignores_non_bash_events(tmp_path: Path) -> None:
    _seed_project(tmp_path, active_tasks=0)
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO),
    }

    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"tool_name": "Read"}),
        text=True,
        capture_output=True,
        env=env,
        timeout=15,
    )

    assert result.returncode == 0
    assert "DISPATCH_QUEUE_READY" not in result.stderr
