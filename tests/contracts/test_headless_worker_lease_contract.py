from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVICE = PROJECT_ROOT / "scripts" / "cos_service_control_plane.py"
DRILL = PROJECT_ROOT / "scripts" / "cos-headless-service-drill"


def run_service(project: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(SERVICE), "--project-dir", str(project), "--json", *args],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=merged_env,
        timeout=20,
    )


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout.strip(), result.stderr
    return json.loads(result.stdout)


def submit(project: Path, task_id: str, command: str) -> None:
    result = run_service(project, "submit", "--kind", "local-command", "--task-id", task_id, "--command", command)
    assert result.returncode == 0, result.stderr + result.stdout


def test_worker_lease_acquire_blocks_renew_release_and_stale_recovery_contract(tmp_path: Path) -> None:
    marker = tmp_path / "ran.txt"
    submit(tmp_path, "task-lease-contract", f"printf ran >> {marker}")

    acquired = run_service(
        tmp_path,
        "worker-run-once",
        "--worker-id",
        "worker-a",
        "--ttl-seconds",
        "60",
        "--simulate-crash-after-lease",
    )
    assert acquired.returncode == 1
    acquired_payload = payload(acquired)
    assert acquired_payload["status"] == "crash_simulated"
    lease_id = acquired_payload["lease_id"]

    blocked = run_service(tmp_path, "worker-run-once", "--worker-id", "worker-b")
    assert blocked.returncode == 0
    assert payload(blocked)["status"] == "idle"
    assert not marker.exists()

    wrong_renew = run_service(tmp_path, "lease-renew", "--lease-id", lease_id, "--worker-id", "worker-b")
    assert wrong_renew.returncode == 1
    assert payload(wrong_renew)["status"] == "blocked"

    renewed = run_service(tmp_path, "lease-renew", "--lease-id", lease_id, "--worker-id", "worker-a", "--ttl-seconds", "120")
    assert renewed.returncode == 0, renewed.stderr + renewed.stdout
    assert payload(renewed)["status"] == "renewed"

    released = run_service(tmp_path, "lease-release", "--lease-id", lease_id, "--worker-id", "worker-a")
    assert released.returncode == 0
    assert payload(released)["status"] == "released"

    recovered = run_service(tmp_path, "worker-run-once", "--worker-id", "worker-b")
    assert recovered.returncode == 0, recovered.stderr + recovered.stdout
    assert payload(recovered)["status"] == "completed"
    assert marker.read_text(encoding="utf-8") == "ran"


def test_two_workers_do_not_complete_same_task_concurrently(tmp_path: Path) -> None:
    marker = tmp_path / "concurrent.txt"
    submit(tmp_path, "task-concurrent-claim", f"printf x >> {marker}")

    workers = [
        subprocess.Popen(
            [
                sys.executable,
                str(SERVICE),
                "--project-dir",
                str(tmp_path),
                "--json",
                "worker-run-once",
                "--worker-id",
                f"worker-{idx}",
            ],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for idx in range(2)
    ]
    results = [worker.communicate(timeout=20) for worker in workers]
    payloads = [json.loads(stdout) for stdout, stderr in results if stdout.strip()]

    completed = [row for row in payloads if row["status"] == "completed"]
    idle = [row for row in payloads if row["status"] == "idle"]
    assert len(completed) == 1, payloads
    assert len(idle) == 1, payloads
    assert marker.read_text(encoding="utf-8") == "x"


def test_restart_idempotency_expires_crashed_lease_and_executes_once(tmp_path: Path) -> None:
    marker = tmp_path / "restart.txt"
    submit(tmp_path, "task-restart-idempotency", f"printf execution >> {marker}")

    crashed = run_service(
        tmp_path,
        "worker-run-once",
        "--worker-id",
        "vm-before-restart",
        "--ttl-seconds",
        "0",
        "--simulate-crash-after-lease",
    )
    assert crashed.returncode == 1
    assert payload(crashed)["status"] == "crash_simulated"
    assert not marker.exists()

    resumed = run_service(tmp_path, "worker-run-once", "--worker-id", "vm-after-restart")
    assert resumed.returncode == 0, resumed.stderr + resumed.stdout
    assert payload(resumed)["status"] == "completed"

    duplicate = run_service(tmp_path, "worker-run-once", "--worker-id", "vm-after-restart-2")
    assert duplicate.returncode == 0
    assert payload(duplicate)["status"] == "idle"
    assert marker.read_text(encoding="utf-8") == "execution"

    drain = run_service(tmp_path, "queue-drain")
    drain_payload = payload(drain)
    assert drain_payload["counts"]["completed"] == 1
    lease_audit = (tmp_path / ".cognitive-os" / "service" / "leases.jsonl").read_text(encoding="utf-8")
    assert '"event_type": "lease_expired"' in lease_audit


def test_container_redacted_artifacts_do_not_include_host_paths(tmp_path: Path) -> None:
    host_root = str(tmp_path)
    submit(tmp_path, "task-no-host-path", "printf portable")

    result = run_service(
        tmp_path,
        "worker-run-once",
        "--worker-id",
        "container-worker",
        env={"COS_REDACT_HOST_PATHS": "1"},
    )
    assert result.returncode == 0, result.stderr + result.stdout
    worker_payload = payload(result)
    assert worker_payload["result"]["artifact_dir"].startswith(".cognitive-os/service/artifacts/")
    assert worker_payload["result"]["workspace"].startswith(".cognitive-os/service/workspaces/")

    service_dir = tmp_path / ".cognitive-os" / "service"
    serialized = "\n".join(
        path.read_text(encoding="utf-8")
        for path in service_dir.rglob("*")
        if path.is_file() and path.suffix in {".json", ".jsonl"}
    )
    assert host_root not in serialized


def test_headless_service_drill_wires_maintainer_dry_run_and_path_redaction() -> None:
    text = DRILL.read_text(encoding="utf-8")
    assert "cos-maintainer-agent --project-dir /workspace --once --dry-run --json" in text
    assert "maintainer_json.get(\"mode\") == \"propose-only\"" in text
    assert "COS_REDACT_HOST_PATHS=1" in text
