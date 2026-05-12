"""Contract tests for ADR-107 human-approved rollback boundary."""
from pathlib import Path
import pytest
pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[2]
SURFACES = [REPO/"packages/auto-repair-rollback/hooks/auto-rollback-trigger.sh", REPO/"packages/auto-repair-rollback/skills/auto-rollback/SKILL.md", REPO/"rules/auto-rollback.md"]
FORBIDDEN = ["auto-execute rollback", "auto-execute without approval", "will execute automatically", "automatically revert", "initiates the rollback"]

def test_auto_rollback_surfaces_require_human_approval() -> None:
    for path in SURFACES:
        text = path.read_text().lower()
        assert "human approval" in text
        assert "destructive" in text

def test_auto_rollback_surfaces_do_not_reintroduce_auto_execute_language() -> None:
    failures = [f"{p.relative_to(REPO)} contains {phrase}" for p in SURFACES for phrase in FORBIDDEN if phrase in p.read_text().lower()]
    assert not failures, "\n".join(failures)

def test_trigger_hook_logs_plan_required_schema() -> None:
    hook = (REPO/"packages/auto-repair-rollback/hooks/auto-rollback-trigger.sh").read_text()
    assert 'mode: "plan_required"' in hook
    assert "approval_required: true" in hook
    assert "destructive_commands_executed: false" in hook
    assert "No git revert" in hook

def test_adr_107_documents_boundary() -> None:
    text = (REPO/"docs/02-Decisions/adrs/ADR-107-human-approved-rollback.md").read_text()
    assert "supersedes the previous phase-aware behavior" in text
    assert "MUST NOT execute" in text
    assert "Every project phase requires human approval" in text
