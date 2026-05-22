"""Tests for Graphify run telemetry joining."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos-graphify-run-telemetry"


def _write_session(path: Path, *, input_tokens: int, output_tokens: int, session_id: str = "session") -> None:
    rows = [
        {
            "type": "assistant",
            "timestamp": "2026-05-22T10:00:00Z",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-20250514",
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_input_tokens": 30,
                    "cache_read_input_tokens": 40,
                },
                "content": [
                    {
                        "type": "tool_use",
                        "id": f"tool-{session_id}",
                        "name": "Read",
                        "input": {"file_path": "lib/harness_adapter/base.py"},
                    }
                ],
            },
        },
        {
            "type": "progress",
            "timestamp": "2026-05-22T10:05:00Z",
            "data": {"type": "agent_progress", "agentId": "agent-a", "message": "done"},
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _write_matrix(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "bundles": [
                    {
                        "key": "harness-events",
                        "label": "Harness event contract",
                        "rationale": "Graphify Phase C.1 identified CanonicalEvent as a hotspot.",
                    }
                ],
                "preload_files": ["lib/harness_adapter/base.py"],
                "inspect_paths": ["lib/harness_adapter/base.py"],
                "tests": [".venv/bin/python -m pytest tests/unit/test_harness_adapter_base.py -q"],
            }
        ),
        encoding="utf-8",
    )


def test_run_telemetry_joins_matrix_with_actual_session_usage(tmp_path: Path) -> None:
    session = tmp_path / "current.jsonl"
    matrix = tmp_path / "matrix.json"
    _write_session(session, input_tokens=1000, output_tokens=250)
    _write_matrix(matrix)

    completed = subprocess.run(
        [str(SCRIPT), "--session", str(session), "--matrix-json", str(matrix), "--json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["metric_label"] == "mixed"
    assert payload["bundle_keys"] == ["harness-events"]
    assert payload["preload_estimate"]["estimated_tokens"] > 0
    assert payload["session_metrics"]["total_input_tokens"] == 1000
    assert payload["session_metrics"]["total_output_tokens"] == 250
    assert payload["session_metrics"]["total_tokens"] == 1250
    assert payload["session_metrics"]["cache_creation_tokens"] == 30
    assert payload["session_metrics"]["cache_read_tokens"] == 40
    assert payload["session_metrics"]["tool_use_count"] == 1
    assert payload["session_metrics"]["subagent_count"] == 1
    assert payload["comparison"]["mode"] == "single-run"


def test_run_telemetry_supports_paired_baseline_without_causal_claim(tmp_path: Path) -> None:
    current = tmp_path / "current.jsonl"
    baseline = tmp_path / "baseline.jsonl"
    matrix = tmp_path / "matrix.json"
    _write_session(current, input_tokens=600, output_tokens=200, session_id="current")
    _write_session(baseline, input_tokens=1000, output_tokens=300, session_id="baseline")
    _write_matrix(matrix)

    completed = subprocess.run(
        [
            str(SCRIPT),
            "--session",
            str(current),
            "--baseline-session",
            str(baseline),
            "--matrix-json",
            str(matrix),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["comparison"]["mode"] == "paired-run"
    assert payload["comparison"]["baseline_total_tokens"] == 1300
    assert payload["comparison"]["current_total_tokens"] == 800
    assert payload["comparison"]["delta_tokens"] == -500
    assert "directional evidence" in payload["comparison"]["interpretation"]


def test_run_telemetry_writes_markdown_report(tmp_path: Path) -> None:
    session = tmp_path / "current.jsonl"
    matrix = tmp_path / "matrix.json"
    out = tmp_path / "report.md"
    _write_session(session, input_tokens=100, output_tokens=50)
    _write_matrix(matrix)

    completed = subprocess.run(
        [str(SCRIPT), "--session", str(session), "--matrix-json", str(matrix), "--out", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert f"COS_GRAPHIFY_RUN_TELEMETRY={out}" in completed.stdout
    report = out.read_text(encoding="utf-8")
    assert "# Graphify Run Telemetry Report" in report
    assert "Metric label: `mixed`" in report
    assert "Actual total input+output tokens: 150" in report
    assert "does not establish before/after token reduction" in report


def test_run_telemetry_can_opt_in_to_latest_claude_session_scan(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "claude-projects"
    project_dir = sessions_dir / "luum-agent-os"
    project_dir.mkdir(parents=True)
    older = project_dir / "older.jsonl"
    latest = project_dir / "latest.jsonl"
    matrix = tmp_path / "matrix.json"
    _write_session(older, input_tokens=100, output_tokens=20, session_id="older")
    _write_session(latest, input_tokens=700, output_tokens=80, session_id="latest")
    _write_matrix(matrix)
    old_time = 1_800_000_000
    new_time = old_time + 60
    older.touch()
    latest.touch()
    import os

    os.utime(older, (old_time, old_time))
    os.utime(latest, (new_time, new_time))

    completed = subprocess.run(
        [
            str(SCRIPT),
            "--latest-claude-session",
            "--sessions-dir",
            str(sessions_dir),
            "--project-filter",
            "luum-agent-os",
            "--matrix-json",
            str(matrix),
            "--json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["session_path"] == str(latest)
    assert payload["session_metrics"]["session_id"] == "latest"
    assert payload["session_metrics"]["total_tokens"] == 780


def test_run_telemetry_rejects_implicit_session_discovery(tmp_path: Path) -> None:
    matrix = tmp_path / "matrix.json"
    _write_matrix(matrix)

    completed = subprocess.run(
        [str(SCRIPT), "--matrix-json", str(matrix), "--json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "one of --session or --latest-claude-session is required" in completed.stderr
