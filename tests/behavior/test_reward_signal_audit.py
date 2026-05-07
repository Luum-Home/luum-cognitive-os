import json
import subprocess

import pytest


@pytest.mark.behavior
def test_reward_signal_audit_cli_reports_quarantined_rows(project_root):
    result = subprocess.run(
        [str(project_root / "scripts" / "cos-reward-signal-audit"), "--stream", "skill-feedback", "--limit", "5", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "reward-signal-audit/v1"
    assert payload["summary"]["total"] <= 5
    assert "skill-feedback" in payload["streams"]
    assert payload["streams"]["skill-feedback"]["summary"]["corrupt"] >= 1


def test_reward_signal_audit_cli_repair_dry_run(project_root, tmp_path):
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)
    (metrics_dir / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )
    (tmp_path / "skills").mkdir()
    contract = tmp_path / "reward-signal-contract.yaml"
    contract.write_text(
        """
schema_version: reward-signal-contract/v1
known_subject_sources:
  skills_dirs: [skills]
streams:
  skill-feedback:
    path: .cognitive-os/metrics/skill-feedback.jsonl
    subject_type: skill
    subject_field: skill
    outcome_field: success
    required_fields: [timestamp, skill, success]
    known_subject_source: skills_dirs
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(project_root / "scripts/cos"),
            "reward-signal",
            "audit",
            "--project-dir",
            str(tmp_path),
            "--contract",
            str(contract),
            "--stream",
            "skill-feedback",
            "--repair",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "reward-signal-repair/v1"
    assert payload["summary"]["quarantined_rows"] == 1
    assert (metrics_dir / "skill-feedback.jsonl").read_text(encoding="utf-8").strip()


@pytest.mark.behavior
def test_cos_reward_signal_audit_route_smoke(project_root):
    result = subprocess.run(
        [str(project_root / "scripts" / "cos"), "reward-signal", "audit", "--stream", "skill-feedback", "--limit", "1", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "reward-signal-audit/v1"
