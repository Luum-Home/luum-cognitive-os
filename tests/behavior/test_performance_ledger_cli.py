import json
import subprocess

import pytest


def _write_blocking_reward_fixture(tmp_path):
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
policy:
  corrupt_ratio_block_threshold: 0.25
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
    return contract


@pytest.mark.behavior
def test_cos_performance_ledger_route_smoke(project_root, tmp_path):
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "performance-ledger",
            "compile",
            "--stream",
            "skill-feedback",
            "--limit",
            "2",
            "--sqlite-path",
            str(tmp_path / "ledger.sqlite"),
            "--jsonl-path",
            str(tmp_path / "ledger.jsonl"),
            "--latest-report-path",
            str(tmp_path / "latest.json"),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "performance-ledger/v1"
    assert payload["summary"]["total"] <= 2
    assert (tmp_path / "ledger.sqlite").exists()
    assert (tmp_path / "ledger.jsonl").exists()
    assert (tmp_path / "latest.json").exists()


@pytest.mark.behavior
def test_cos_performance_ledger_default_compile_accepts_flags(project_root, tmp_path):
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "performance-ledger",
            "--stream",
            "skill-feedback",
            "--limit",
            "1",
            "--sqlite-path",
            str(tmp_path / "ledger.sqlite"),
            "--jsonl-path",
            str(tmp_path / "ledger.jsonl"),
            "--latest-report-path",
            str(tmp_path / "latest.json"),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "performance-ledger/v1"


def test_cos_performance_ledger_require_consumable_exits_two_when_policy_blocks(project_root, tmp_path):
    contract = _write_blocking_reward_fixture(tmp_path)
    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos"),
            "performance-ledger",
            "compile",
            "--project-dir",
            str(tmp_path),
            "--contract",
            str(contract),
            "--stream",
            "skill-feedback",
            "--limit",
            "1",
            "--sqlite-path",
            str(tmp_path / "ledger.sqlite"),
            "--jsonl-path",
            str(tmp_path / "ledger.jsonl"),
            "--latest-report-path",
            str(tmp_path / "latest.json"),
            "--require-consumable",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["consumption_policy"]["can_consume_all"] is False
