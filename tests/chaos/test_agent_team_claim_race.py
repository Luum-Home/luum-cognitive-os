from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

import pytest

from lib.agent_team import AgentTeam


def _claim(project: str, queue: mp.Queue) -> None:
    team = AgentTeam("release", project_dir=project)
    task = team.claim_next(session_id=mp.current_process().name)
    queue.put(task.task_id if task else None)


@pytest.mark.chaos
def test_agent_team_claim_next_is_single_winner_across_processes(tmp_path: Path) -> None:
    team = AgentTeam("release", project_dir=tmp_path)
    team.create_task("Only one worker can own this", task_id="one")
    queue: mp.Queue = mp.Queue()
    processes = [mp.Process(target=_claim, args=(str(tmp_path), queue), name=f"worker-{idx}") for idx in range(6)]

    for proc in processes:
        proc.start()
    for proc in processes:
        proc.join(timeout=10)
        assert proc.exitcode == 0

    results = [queue.get(timeout=1) for _ in processes]
    assert results.count("one") == 1
    assert results.count(None) == 5
