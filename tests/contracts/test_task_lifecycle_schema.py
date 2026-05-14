from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = REPO_ROOT / "manifests" / "task-lifecycle-schema.yaml"
ADR = REPO_ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-162-task-lifecycle-interruption-question-worktree-pr-protocol.md"
MANUAL = REPO_ROOT / "docs" / "09-Quality" / "manual-tests" / "task-lifecycle-worktree-pr-flow.md"

REQUIRED_TASK_STATUSES = {
    "queued",
    "claimed",
    "running",
    "paused",
    "interrupted",
    "waiting_for_human",
    "needs_human",
    "resumable",
    "validating",
    "pr_ready",
    "changes_requested",
    "approved",
    "completed",
    "merged",
    "failed",
    "cancelled",
    "abandoned",
}

REQUIRED_QUESTION_TYPES = {
    "requirement",
    "approval",
    "credential",
    "conflict",
    "product_decision",
    "clarification",
    "review",
}

REQUIRED_INTERRUPTION_REASONS = {
    "operator_interrupt",
    "compaction",
    "crash",
    "auth_required",
    "path_conflict",
    "merge_conflict",
    "policy_block",
}

REQUIRED_EVENTS = {
    "task.created",
    "task.interrupted",
    "task.resumed",
    "question.asked",
    "question.answered",
    "worktree.created",
    "branch.created",
    "pr.created",
    "pr.merged",
}


def _schema() -> dict:
    return yaml.safe_load(SCHEMA.read_text())


def test_task_lifecycle_schema_contract() -> None:
    data = _schema()
    assert data["schema_version"] == "task-lifecycle.v1"
    assert str(data["review_date"]) == "2026-05-05"
    assert data["proof_level"] == "contract-only"
    assert "Remote ingress adapters enqueue intent; they never execute tools directly." in data["principles"]


def test_task_states_are_complete_and_transitioned() -> None:
    statuses = _schema()["task"]["statuses"]
    assert REQUIRED_TASK_STATUSES <= set(statuses)

    for status, metadata in statuses.items():
        assert "terminal" in metadata, status
        assert "description" in metadata, status
        assert "allowed_next" in metadata, status
        if metadata["terminal"]:
            assert metadata["allowed_next"] == [], status
        else:
            assert metadata["allowed_next"], status

    assert "waiting_for_human" in statuses["running"]["allowed_next"]
    assert "resumable" in statuses["interrupted"]["allowed_next"]
    assert "merged" in statuses["approved"]["allowed_next"]


def test_questions_interruptions_and_events_are_structured() -> None:
    data = _schema()
    assert REQUIRED_QUESTION_TYPES <= set(data["question"]["types"])
    assert REQUIRED_INTERRUPTION_REASONS <= set(data["interruption"]["reasons"])
    assert REQUIRED_EVENTS <= set(data["communication"]["event_channel"]["event_types"])

    for field in ["question_id", "task_id", "type", "blocking", "question", "options"]:
        assert field in data["question"]["required_fields"]
    for field in ["interrupt_id", "task_id", "reason", "resumable", "resume_command"]:
        assert field in data["interruption"]["required_fields"]


def test_worktree_branch_and_pr_publication_rules() -> None:
    data = _schema()
    assert data["worktree"]["path_template"] == ".worktrees/{task_id}"
    assert data["worktree"]["branch_template"] == "codex/{task_id}-{slug}"
    assert "missing_evidence" in data["worktree"]["cleanup_policy"]["never_delete_when"]

    pr = data["pull_request"]
    assert "draft_pr_created" in pr["statuses"]
    assert "merged" in pr["statuses"]
    assert "Rollback" in pr["required_body_sections"]
    assert "direct_push_main" in pr["blocked_actions"]
    assert "merge_without_human_or_merge_queue_approval" in pr["blocked_actions"]


def test_adr_and_manual_test_reference_schema() -> None:
    adr_text = ADR.read_text()
    manual_text = MANUAL.read_text()
    assert "manifests/task-lifecycle-schema.yaml" in adr_text
    assert "tests/contracts/test_task_lifecycle_schema.py" in adr_text
    assert "manifests/task-lifecycle-schema.yaml" in manual_text
    assert "contract-only" in manual_text
