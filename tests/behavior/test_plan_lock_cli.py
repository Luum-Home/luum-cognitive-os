from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "plan-lock.sh"


def run(tmp_path: Path, *args: str, session: str = "s1", ttl: str = "1800") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["COGNITIVE_OS_SESSION_ID"] = session
    env["COS_PLAN_LOCK_TTL"] = ttl
    return subprocess.run([str(SCRIPT), *args], text=True, capture_output=True, env=env, check=False)


def test_plan_lock_blocks_second_session_and_releases(tmp_path: Path) -> None:
    plan = ".cognitive-os/plans/demo.md"

    first = run(tmp_path, "acquire", plan, "close-item", session="s1")
    # Make the lock look held by this live pytest process so the second session
    # exercises the conflict path instead of stale-dead-pid replacement.
    meta = next((tmp_path / ".cognitive-os" / "runtime" / "plan-locks").glob("*.lock/metadata.json"))
    meta.write_text(meta.read_text().replace('"pid":', f'"pid":{os.getpid()},"old_pid":'), encoding="utf-8")
    second = run(tmp_path, "acquire", plan, "close-item", session="s2")
    release = run(tmp_path, "release", plan, session="s1")
    third = run(tmp_path, "acquire", plan, "close-item", session="s2")

    assert first.returncode == 0, first.stderr
    assert second.returncode == 2
    assert '"session_id":"s1"' in second.stderr
    assert release.returncode == 0
    assert third.returncode == 0, third.stderr


def test_plan_lock_replaces_stale_dead_pid_lock(tmp_path: Path) -> None:
    plan = ".cognitive-os/plans/demo.md"
    first = run(tmp_path, "acquire", plan, session="s1")
    assert first.returncode == 0
    # The lock holder process is already gone, so a later acquire may replace it.
    second = run(tmp_path, "acquire", plan, session="s2")
    assert second.returncode == 0, second.stderr
    assert "stale-replaced" in second.stderr
