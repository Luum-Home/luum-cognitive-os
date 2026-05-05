"""Tests for consumer improvement proposal export/import."""
from __future__ import annotations

import json
from pathlib import Path

from lib.consumer_improvement_proposals import (
    SCHEMA_VERSION,
    build_consumer_improvement_bundle,
    import_consumer_improvement_bundle,
    sanitize_text,
    write_consumer_improvement_bundle,
)


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def test_export_builds_sanitized_skill_and_error_proposals(tmp_path: Path) -> None:
    skill = tmp_path / "skills" / "sdd-apply" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: sdd-apply\n---\n", encoding="utf-8")
    for _ in range(3):
        _append_jsonl(tmp_path / ".cognitive-os" / "metrics" / "skill-feedback.jsonl", {"skill": "sdd-apply", "success": False})
    for _ in range(3):
        _append_jsonl(
            tmp_path / ".cognitive-os" / "metrics" / "error-learning.jsonl",
            {
                "type": "TEST_FAILURE",
                "service": "billing",
                "message": "failed with token=sk-supersecretvalue and path " + "/" + "Users/alice/project",
            },
        )

    bundle = build_consumer_improvement_bundle(tmp_path, project="consumer-api", profile="core", threshold=3)

    assert bundle["schema_version"] == SCHEMA_VERSION
    assert bundle["mode"] == "propose_only"
    assert bundle["policy"]["auto_merge"] is False
    assert bundle["proposal_count"] >= 2
    actions = {proposal["action"] for proposal in bundle["proposals"]}
    assert "upstream-candidate" in actions
    assert "project-local" in actions
    raw = json.dumps(bundle)
    assert "sk-supersecretvalue" not in raw
    assert "/" + "Users/alice" not in raw
    assert "[REDACTED]" in raw


def test_import_is_propose_only_and_writes_review_artifact(tmp_path: Path) -> None:
    bundle = build_consumer_improvement_bundle(tmp_path, project="consumer-api")
    bundle["proposals"] = [
        {
            "proposal_id": "p1",
            "action": "project-local",
            "title": "Improve local skill",
            "summary": "summary",
            "primitive_id": "skills/local",
            "evidence": {"count": 3},
            "required_tests": [],
            "human_approval_required": True,
            "runtime_effect": "none",
            "blocked_actions": ["auto_merge"],
        }
    ]
    bundle["proposal_count"] = 1
    source = tmp_path / "bundle.json"
    write_consumer_improvement_bundle(bundle, source)

    result = import_consumer_improvement_bundle(tmp_path, source)

    assert result["status"] == "proposed"
    assert result["runtime_effect"] == "none"
    written = Path(result["written_to"])
    assert written.exists()
    artifact = json.loads(written.read_text(encoding="utf-8"))
    assert artifact["policy"]["no_runtime_mutation"] is True
    assert not (tmp_path / "manifests" / "primitive-lifecycle.yaml").exists()


def test_import_rejects_runtime_mutating_bundle(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "proposals": [{"action": "upstream-candidate", "runtime_effect": "mutate"}],
            }
        ),
        encoding="utf-8",
    )

    result = import_consumer_improvement_bundle(tmp_path, source)

    assert result["status"] == "fail"
    assert result["runtime_effect"] == "none"
    assert not (tmp_path / ".cognitive-os" / "improvements" / "proposals").exists()


def test_sanitize_text_redacts_common_secret_and_home_path() -> None:
    text = sanitize_text("Authorization: Bearer abc123secret token=sk-live-secret " + "/" + "home/matias/project")

    assert "abc123secret" not in text
    assert "sk-live-secret" not in text
    assert "/" + "home/matias" not in text
    assert "[REDACTED]" in text
