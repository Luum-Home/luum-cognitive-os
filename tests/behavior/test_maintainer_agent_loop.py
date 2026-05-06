import json
import subprocess

import pytest


@pytest.mark.behavior
def test_maintainer_agent_dry_run_blocks_when_signal_quality_is_dirty(project_root, tmp_path):
    skill_dir = tmp_path / "skills" / "docs-to-artifact"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: docs-to-artifact\n---\n", encoding="utf-8")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos-maintainer-agent"),
            "--project-dir",
            str(tmp_path),
            "--once",
            "--dry-run",
            "--stream",
            "skill-feedback",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked_by_signal_quality"
    assert payload["promotion"]["proposal_count"] == 0
    assert payload["mode"] == "propose-only"


@pytest.mark.behavior
def test_maintainer_agent_dry_run_generates_one_human_approved_proposal(project_root, tmp_path):
    skill_dir = tmp_path / "skills" / "docs-to-artifact"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\nname: docs-to-artifact\n---\n", encoding="utf-8")
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "skill-feedback.jsonl").write_text(
        '{"timestamp":"2026-05-06T00:00:00Z","skill":"docs-to-artifact","success":true}\n'
        '{"timestamp":"2026-05-06T00:00:01Z","skill":"docs-to-artifact","success":false}\n'
        '{"timestamp":"2026-05-06T00:00:02Z","skill":"matias","success":false}\n',
        encoding="utf-8",
    )
    contract = tmp_path / "reward-signal-contract.yaml"
    contract.write_text(
        (project_root / "manifests" / "reward-signal-contract.yaml").read_text(encoding="utf-8").replace(
            "corrupt_ratio_block_threshold: 0.25", "corrupt_ratio_block_threshold: 0.34"
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(project_root / "scripts" / "cos-maintainer-agent"),
            "--project-dir",
            str(tmp_path),
            "--once",
            "--dry-run",
            "--contract",
            str(contract),
            "--stream",
            "skill-feedback",
            "--day-window",
            "2026-05-06",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert payload["promotion"]["proposal_count"] == 1
    proposal = payload["promotion"]["proposals"][0]
    assert proposal["human_approval_required"] is True
    assert proposal["harness_scope"] == "harness-agnostic"
    assert payload["written_proposal_paths"] == []
