from __future__ import annotations

from pathlib import Path

import yaml

from scripts.primitive_lifecycle import validate_manifest

ROOT = Path(__file__).resolve().parents[2]


def _yaml(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_agent_control_skill_exists_with_operator_routes() -> None:
    text = (ROOT / "skills" / "agent-control" / "SKILL.md").read_text(encoding="utf-8")

    assert "name: agent-control" in text
    assert "routing_patterns:" in text
    assert "stop" in text
    assert "answer" in text
    assert "kill" in text
    assert "list-live" in text
    assert "Contextual Trigger" in text
    assert "scripts/orchestrator.py control" in text
    assert "scripts/orchestrator.py answer" in text


def test_bidirectional_control_primitives_have_lifecycle_rows() -> None:
    manifest = _yaml("manifests/primitive-lifecycle.yaml")
    by_id = {row["id"]: row for row in manifest["primitives"]}

    required = {
        "scripts/orchestrator.py",
        "packages/agent-coordination/lib/agent_bus.py#filesystem-interrupt",
        "hooks/agent-control-inbound-guard.sh",
        "packages/agent-lifecycle/lib/harness_adapter/base.py#inbound-signal",
        "skills/agent-control/SKILL.md",
    }
    assert required <= by_id.keys()

    assert by_id["hooks/agent-control-inbound-guard.sh"]["lifecycle_state"] == "blocking"
    assert by_id["packages/agent-coordination/lib/agent_bus.py#filesystem-interrupt"]["maturity"] == "blocking"
    assert by_id["scripts/orchestrator.py"]["risk_class"] == "mutating"
    assert "control" in by_id["scripts/orchestrator.py"]["behavior_evidence"]
    assert "inbound_signal" in by_id["packages/agent-lifecycle/lib/harness_adapter/base.py#inbound-signal"]["behavior_evidence"]


def test_bidirectional_control_primitives_have_behavior_evidence() -> None:
    evidence = _yaml("manifests/primitive-behavior-evidence.yaml")
    rows = {row["primitive"]: row for row in evidence["evidence"]}

    for primitive in (
        "scripts/orchestrator.py",
        "packages/agent-coordination/lib/agent_bus.py#filesystem-interrupt",
        "hooks/agent-control-inbound-guard.sh",
        "packages/agent-lifecycle/lib/harness_adapter/base.py#inbound-signal",
        "skills/agent-control/SKILL.md",
    ):
        assert primitive in rows
        assert rows[primitive]["tests"]

    assert "tests/integration/test_orchestrator_cli.py" in rows["scripts/orchestrator.py"]["tests"]
    assert "tests/integration/test_agent_control_inbound_guard.py" in rows["hooks/agent-control-inbound-guard.sh"]["tests"]


def test_agent_control_hook_is_classified_for_projection() -> None:
    manifest = _yaml("manifests/hook-registration-classification.yaml")
    rows = {row["path"]: row for row in manifest["entries"]}

    row = rows["hooks/agent-control-inbound-guard.sh"]
    assert row["status"] == "active"
    assert "inbound" in row["rationale"]


def test_agent_communication_rule_mentions_current_control_surfaces() -> None:
    text = (ROOT / "packages" / "agent-coordination" / "rules" / "agent-communication.md").read_text(encoding="utf-8")

    assert "scripts/orchestrator.py control" in text
    assert "scripts/orchestrator.py answer" in text
    assert "hooks/agent-control-inbound-guard.sh" in text
    assert "interrupt" in text
    assert "inbound_signal" in text
    assert "/agent-control" in text
    assert "pending sunset" in text


def test_cos_agent_message_is_marked_as_pending_sunset() -> None:
    manifest = _yaml("manifests/primitive-lifecycle.yaml")
    row = next(item for item in manifest["primitives"] if item["id"] == "scripts/cos-agent-message")

    assert row["lifecycle_state"] == "pending-sunset"
    assert "/agent-control" in row["sunset_criteria"]
    assert "cosd" in row["sunset_criteria"]


def test_lifecycle_validator_accepts_agent_control_transition_types() -> None:
    primitive = {
        "id": "lib/example#signal",
        "kind": "library",
        "owner_adr": "ADR-042",
        "lifecycle_state": "pending-sunset",
        "maturity": "advisory",
        "distribution": "core",
        "governance_class": "runtime-safety",
        "risk_class": "advisory",
        "supported_harnesses": ["claude", "codex"],
        "projection_targets": ["lib/example.py"],
        "evidence_commands": ["python3 -m pytest tests/contracts/test_agent_control_primitive_lifecycle.py -q"],
        "exit_behavior": "mixed",
        "metrics_file": ".cognitive-os/example.jsonl",
        "docs_claim_level": "advisory",
        "rollback_or_repair_command": "Remove the signal row and use direct control artifacts.",
        "sunset_criteria": "Archive when the successor has equivalent control tests.",
    }

    findings = validate_manifest({"schema_version": 1, "primitives": [primitive]})

    assert findings == []
