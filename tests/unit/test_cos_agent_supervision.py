from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "cos_agent_supervision.py"


def run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, timeout=30)
    if check and result.returncode != 0:
        raise AssertionError(f"command failed {cmd}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def init_repo(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    run(["git", "init", "--bare", str(remote)], tmp_path)
    run(["git", "clone", str(remote), str(repo)], tmp_path)
    run(["git", "switch", "-c", "main"], repo)
    run(["git", "config", "user.email", "test@example.com"], repo)
    run(["git", "config", "user.name", "Test User"], repo)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    run(["git", "add", "README.md"], repo)
    run(["git", "commit", "-m", "base"], repo)
    run(["git", "push", "-u", "origin", "main"], repo)
    return repo


def test_status_reports_dead_with_wip_in_spanish(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "wip.txt").write_text("work\n", encoding="utf-8")

    result = run([str(ROOT / "scripts" / "cos-agent-run-status"), "--project-dir", str(repo), "--process-id", "missing-agent-xyz", "--language", "es", "--json"], repo)
    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "cos.agent-run-status.v1"
    assert payload["state"] == "dead-with-wip"
    assert "muerto con WIP" in payload["state_label"]
    assert payload["dirty_count"] == 1
    assert payload["ahead_behind"] == {"base_ref": "origin/main", "ahead": 0, "behind": 0}


def test_watch_detects_repeated_status_as_probably_stuck(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)

    result = run([
        str(ROOT / "scripts" / "cos-agent-watch"),
        "--project-dir", str(repo),
        "--process-id", "pytest-self",
        "--pid", str(os.getpid()),
        "--no-progress-threshold", "1",
        "--max-cycles", "2",
        "--interval", "0",
        "--json",
    ], repo, check=False)
    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "cos.agent-watch.v1"
    assert payload["cycles"][-1]["state"] in {"probably-stuck", "idle-but-safe"}
    assert (repo / ".cognitive-os/agent-runs/pytest-self/watch.jsonl").exists()


def test_progress_metric_contract_extracts_json_metric(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    contract = repo / "progress.yaml"
    contract.write_text(
        "progress:\n"
        "  metric: residual\n"
        "  command: >-\n"
        "    python3 -c \"print(410)\"\n"
        "  improves_when: decreases\n"
        "  stuck_after: 3\n",
        encoding="utf-8",
    )

    result = run([str(ROOT / "scripts" / "cos-progress-metric"), "--project-dir", str(repo), "--process-id", "hir", "--contract", str(contract), "--json"], repo)
    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "cos.progress-metric.v1"
    assert payload["progress_metric"]["metric"] == "residual"
    assert payload["progress_metric"]["value"] == 410


def test_handoff_if_dead_writes_markdown_summary(tmp_path: Path) -> None:
    repo = init_repo(tmp_path)
    (repo / "wip.txt").write_text("work\n", encoding="utf-8")

    result = run([str(ROOT / "scripts" / "cos-handoff-if-dead"), "--project-dir", str(repo), "--process-id", "missing-agent-xyz", "--language", "en", "--json"], repo)
    payload = json.loads(result.stdout)

    assert payload["schema_version"] == "cos.agent-handoff.v1"
    handoff = Path(payload["handoff_path"])
    assert handoff.exists()
    text = handoff.read_text(encoding="utf-8")
    assert "Agent Run Handoff" in text
    assert "dead-with-wip" in text
