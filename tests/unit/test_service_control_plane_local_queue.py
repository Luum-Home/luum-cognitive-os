from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "cos_service_control_plane.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import cos_service_control_plane as scp  # noqa: E402


def test_submit_and_worker_run_once_writes_artifact_bundle(tmp_path: Path) -> None:
    submitted = scp.submit_task(
        tmp_path,
        kind="local-command",
        command="printf ok > result.txt",
        task_id="demo",
    )
    assert submitted["status"] == "submitted"

    result = scp.worker_run_once(tmp_path, worker_id="test-worker")

    assert result["status"] == "completed"
    assert result["task_id"] == "demo"
    artifact_dir = Path(result["result"]["artifact_dir"])
    workspace = Path(result["result"]["workspace"])
    assert (workspace / "result.txt").read_text(encoding="utf-8") == "ok"
    for name in ["task.json", "lease.json", "executor.json", "result.json", "redaction-report.json"]:
        assert (artifact_dir / name).exists(), name
    assert (artifact_dir / "logs" / "stdout.txt").exists()
    assert (artifact_dir / "logs" / "stderr.txt").exists()

    drained = scp.queue_drain(tmp_path)
    assert drained["counts"]["completed"] == 1
    assert drained["active_task_ids"] == []


def test_worker_is_idle_without_pending_tasks(tmp_path: Path) -> None:
    result = scp.worker_run_once(tmp_path)

    assert result == {"ok": True, "status": "idle", "reason": "no pending tasks"}


def test_failed_local_command_records_failed_task(tmp_path: Path) -> None:
    scp.submit_task(tmp_path, kind="local-command", command="exit 7", task_id="bad")

    result = scp.worker_run_once(tmp_path, worker_id="test-worker")

    assert result["status"] == "failed"
    assert result["result"]["returncode"] == 7
    drained = scp.queue_drain(tmp_path)
    assert drained["counts"]["failed"] == 1


def test_secret_like_output_is_redacted_from_logs(tmp_path: Path) -> None:
    scp.submit_task(tmp_path, kind="local-command", command="printf 'ANTHROPIC_API_KEY=sk-ant-secret1234567890'", task_id="secret")

    result = scp.worker_run_once(tmp_path, worker_id="test-worker")

    artifact_dir = Path(result["result"]["artifact_dir"])
    stdout = (artifact_dir / "logs" / "stdout.txt").read_text(encoding="utf-8")
    report = json.loads((artifact_dir / "redaction-report.json").read_text(encoding="utf-8"))
    assert "sk-ant-secret" not in stdout
    assert "[REDACTED]" in stdout
    assert report["total_redactions"] >= 1


def test_cli_submit_worker_and_drain(tmp_path: Path) -> None:
    submit = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "submit",
            "--kind",
            "local-command",
            "--task-id",
            "cli-demo",
            "--command",
            "printf cli > cli.txt",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert submit.returncode == 0, submit.stderr
    assert json.loads(submit.stdout)["status"] == "submitted"

    worker = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--project-dir",
            str(tmp_path),
            "--json",
            "worker-run-once",
            "--worker-id",
            "cli-worker",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert worker.returncode == 0, worker.stderr + worker.stdout
    assert json.loads(worker.stdout)["status"] == "completed"

    drain = subprocess.run(
        [sys.executable, str(SCRIPT), "--project-dir", str(tmp_path), "--json", "queue-drain"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert drain.returncode == 0, drain.stderr
    payload = json.loads(drain.stdout)
    assert payload["counts"]["completed"] == 1


def test_phase_one_rejects_provider_executor(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="local-command"):
        scp.submit_task(
            tmp_path,
            kind="local-command",
            command="printf nope",
            executor_id="codex-cli-host",
        )


def test_expired_crash_lease_allows_resume(tmp_path: Path) -> None:
    scp.submit_task(tmp_path, kind="local-command", command="printf resumed > resumed.txt", task_id="resume")

    crashed = scp.worker_run_once(
        tmp_path,
        worker_id="crashing-worker",
        ttl_seconds=0,
        simulate_crash_after_lease=True,
    )
    assert crashed["status"] == "crash_simulated"

    drained = scp.queue_drain(tmp_path)
    assert drained["expired_leases"]
    assert drained["counts"]["pending"] == 1

    resumed = scp.worker_run_once(tmp_path, worker_id="resuming-worker")
    assert resumed["status"] == "completed"
    assert Path(resumed["result"]["workspace"], "resumed.txt").read_text(encoding="utf-8") == "resumed"


def test_provider_host_adapter_defaults_to_needs_human_without_provider_call(tmp_path: Path) -> None:
    scp.submit_task(
        tmp_path,
        kind="provider",
        command=None,
        executor_id="codex-cli-host",
        prompt="Summarize this temporary repository.",
        task_id="provider-dry",
        dry_run=True,
    )

    result = scp.worker_run_once(tmp_path, worker_id="provider-worker")

    assert result["status"] == "needs_human"
    assert result["result"]["provider_calls"] == 0
    artifact_dir = Path(result["result"]["artifact_dir"])
    executor = json.loads((artifact_dir / "executor.json").read_text(encoding="utf-8"))
    assert executor["executor_id"] == "codex-cli-host"
    assert executor["credential_mode"] == "account-session"
