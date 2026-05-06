from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

REPO = Path(__file__).resolve().parents[2]
COSD = REPO / "scripts" / "cosd"
HOOK = REPO / "hooks" / "cosd-intent-submit.sh"


def run_cosd(project: Path, *args: str) -> dict:
    result = subprocess.run(
        ["bash", str(COSD), "--project-dir", str(project), "--json", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def wait_result(project: Path, intent_id: str) -> dict:
    path = project / ".cognitive-os" / "cosd" / "results" / f"{intent_id}.json"
    deadline = time.time() + 5
    while time.time() < deadline:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        time.sleep(0.05)
    raise AssertionError(f"missing result for {intent_id}")


def test_cosd_start_arbitrates_competing_adr_numbers_and_stops(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-001-existing.md").write_text("# ADR-001: Existing\n", encoding="utf-8")

    try:
        started = run_cosd(tmp_path, "start", "--interval-seconds", "0.05")
        assert started["status"] == "running"
        assert isinstance(started["pid"], int)

        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "intent-a",
            "--session-id",
            "s1",
            "--topic",
            "Alpha surface",
            "--filename-stem",
            "alpha-surface",
        )
        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "intent-b",
            "--session-id",
            "s2",
            "--topic",
            "Beta surface",
            "--filename-stem",
            "beta-surface",
        )

        a = wait_result(tmp_path, "intent-a")
        b = wait_result(tmp_path, "intent-b")
        assert {a["decision"]["adr_number"], b["decision"]["adr_number"]} == {2, 3}

        status = run_cosd(tmp_path, "status")
        assert status["intent_queue_depth"] == 0
        assert len(status["last_arbitrations"]) >= 2
    finally:
        stopped = run_cosd(tmp_path, "stop")
        assert stopped["status"] == "stopped"


def test_cosd_rejects_tombstone_for_active_adr(tmp_path: Path) -> None:
    adrs = tmp_path / "docs" / "adrs"
    adrs.mkdir(parents=True)
    (adrs / "ADR-171-active-decision.md").write_text("# ADR-171: Active\n", encoding="utf-8")

    try:
        run_cosd(tmp_path, "start", "--interval-seconds", "0.05")
        run_cosd(
            tmp_path,
            "submit-intent",
            "--kind",
            "adr-tombstone-request",
            "--intent-id",
            "intent-tombstone",
            "--session-id",
            "s3",
            "--adr-number",
            "171",
            "--candidate-filename",
            "ADR-171-tombstone.md",
        )
        result = wait_result(tmp_path, "intent-tombstone")
        assert result["status"] == "rejected"
        assert result["decision"]["adr_number"] == 171
    finally:
        run_cosd(tmp_path, "stop")


def test_cosd_intent_submit_hook_uses_daemon_cli(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            "bash",
            str(HOOK),
            "submit-intent",
            "--kind",
            "adr-number-request",
            "--intent-id",
            "hook-intent",
            "--session-id",
            "hook-session",
            "--topic",
            "Hook submitted",
        ],
        cwd=REPO,
        env={"CLAUDE_PROJECT_DIR": str(tmp_path), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".cognitive-os" / "cosd" / "intents" / "hook-intent.json").exists()
