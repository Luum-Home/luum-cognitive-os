import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "hooks" / "session-quality-close-gate.sh"


def run_hook(project_dir: Path, session_id: str = "test-session"):
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["COGNITIVE_OS_SESSION_ID"] = session_id
    return subprocess.run(
        ["bash", str(HOOK)],
        input="{}",
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_session_quality_close_gate_allows_without_metrics(tmp_path):
    result = run_hook(tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_session_quality_close_gate_blocks_failed_auto_verify(tmp_path):
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "auto-verify.jsonl").write_text(
        json.dumps({"status": "failed", "message": "unit lane red"}) + "\n",
        encoding="utf-8",
    )

    result = run_hook(tmp_path)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "block"
    assert "unit lane red" in payload["reason"]


def test_session_quality_close_gate_blocks_session_scoped_failed_counts(tmp_path):
    metrics = tmp_path / ".cognitive-os" / "sessions" / "abc" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "completion-gate.jsonl").write_text(
        json.dumps({"summary": {"blocking_failures": 2}, "reason": "missing acceptance evidence"}) + "\n",
        encoding="utf-8",
    )

    result = run_hook(tmp_path, session_id="abc")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "block"
    assert "missing acceptance evidence" in payload["reason"]
