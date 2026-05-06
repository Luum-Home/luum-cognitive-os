import json
import subprocess

import pytest


@pytest.mark.behavior
def test_cos_run_trace_cli_reconstructs_fixture_session_without_private_payload(project_root, tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "dispatch-gate.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","session_id":"fixture-session","action":"allow"}\n',
        encoding="utf-8",
    )
    (metrics / "private-content-access.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:01Z","session_id":"fixture-session","path":".cognitive-os/strategy/private.md","payload":"raw private payload"}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos-run-trace"),
            "--project-dir",
            str(tmp_path),
            "--session-id",
            "fixture-session",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    assert "raw private payload" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "run-flight-recorder/v1"
    assert payload["event_count"] == 2
    assert payload["final_status"] == "joined"


@pytest.mark.behavior
def test_cos_observe_run_route_smoke(project_root, tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "hook-timing.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","run_id":"route-run","hook":"x"}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "observe",
            "run",
            "--project-dir",
            str(tmp_path),
            "--run-id",
            "route-run",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["run_id"] == "route-run"
    assert payload["streams"] == {"hook-timing": 1}
