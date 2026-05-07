import json
import subprocess

import pytest


@pytest.mark.behavior
def test_skill_performance_ledger_cli_blocks_corrupt_skill_rows_from_lifecycle_status(project_root, tmp_path):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "reward-signal-contract.yaml").write_text(
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
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"matias","success":true}\n',
        encoding="utf-8",
    )
    (tmp_path / "skills").mkdir()

    result = subprocess.run(
        [str(project_root / "scripts" / "cos-skill-performance-ledger"), "--project-dir", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "skill-performance-ledger/v1"
    assert payload["status"] == "quarantined-input"
    assert payload["reward_signal_quality"]["corrupt"] == 1
    assert payload["lifecycle"]["promotion_candidates"] == []

