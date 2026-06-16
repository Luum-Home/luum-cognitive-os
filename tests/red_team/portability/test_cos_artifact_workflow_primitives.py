# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WRAPPERS = [
    "cos-artifact-ingest",
    "cos-artifact-watch",
    "cos-artifact-report",
    "cos-work-graph",
    "cos-refutation-review",
    "cos-second-pass-advisor",
]


def run_wrapper(name: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(ROOT / "scripts" / name), *args], cwd=cwd, text=True, capture_output=True, timeout=30, check=False)


def test_artifact_workflow_wrappers_exist_and_are_valid_bash() -> None:
    for name in WRAPPERS:
        artifact = ROOT / "scripts" / name
        assert artifact.exists(), name
        assert artifact.stat().st_mode & 0o111, name
        subprocess.run(["bash", "-n", str(artifact)], cwd=ROOT, check=True)


def test_artifact_workflow_wrappers_run_from_arbitrary_consumer_cwd(tmp_path: Path) -> None:
    project = tmp_path / "consumer"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    artifacts = project / "evidence"
    artifacts.mkdir()
    (artifacts / "note.md").write_text("claim verified\n", encoding="utf-8")

    ingest = run_wrapper("cos-artifact-ingest", outside, "--project-dir", str(project), "--artifact-dir", str(artifacts), "--json")
    assert ingest.returncode == 0, ingest.stderr + ingest.stdout
    assert json.loads(ingest.stdout)["added"] == 1

    report = run_wrapper("cos-artifact-report", outside, "--project-dir", str(project), "--json")
    assert report.returncode == 0, report.stderr + report.stdout
    assert json.loads(report.stdout)["artifact_count"] == 1

    graph = run_wrapper("cos-work-graph", outside, "add", "--project-dir", str(project), "--graph-id", "g", "--task-id", "T1", "--title", "review artifact", "--json")
    assert graph.returncode == 0, graph.stderr + graph.stdout
    assert json.loads(graph.stdout)["task_count"] == 1

    refute = run_wrapper("cos-refutation-review", outside, "--project-dir", str(project), "--process-id", "p", "--claim-id", "C1", "--claim", "artifact reviewed", "--evidence", "note.md", "--verification-command", "python3 -c 'raise SystemExit(0)'", "--json")
    assert refute.returncode == 0, refute.stderr + refute.stdout
    assert json.loads(refute.stdout)["verdict"] == "supported"

    advisor = run_wrapper("cos-second-pass-advisor", outside, "--project-dir", str(project), "--process-id", "p", "--signal", "claim", "--command", "python3 -c 'print(\"ok\")'", "--json")
    assert advisor.returncode == 0, advisor.stderr + advisor.stdout
    payload = json.loads(advisor.stdout)
    assert payload["triggered"] is True
    assert payload["result"]["passed"] is True
