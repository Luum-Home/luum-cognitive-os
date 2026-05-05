from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = REPO_ROOT / "manifests" / "host-cli-bridge-contract.yaml"
ADR = REPO_ROOT / "docs" / "adrs" / "ADR-164-host-cli-bridge-security-boundary.md"
ARCH = REPO_ROOT / "docs" / "architecture" / "host-cli-bridge-security-boundary.md"
MANUAL = REPO_ROOT / "docs" / "manual-tests" / "host-cli-bridge-security-boundary.md"


def _contract() -> dict:
    return yaml.safe_load(CONTRACT.read_text())


def test_host_cli_bridge_contract_deny_by_default() -> None:
    data = _contract()
    assert data["schema_version"] == "host-cli-bridge-contract.v1"
    assert data["status"] == "design-only"
    assert data["profile"] == "host-cli-bridge"
    assert data["transport"]["default_bind"] == "localhost-only"
    assert data["transport"]["remote_bind"] == "forbidden-by-default"
    assert data["authorization"]["command_allowlist_required"] is True
    assert data["approval"]["default_policy"] == "deny-provider-calls"
    assert data["approval"]["provider_calls_require_human_approval"] is True


def test_credential_store_copy_and_secret_paths_are_blocked() -> None:
    blocked = set(_contract()["blocked_paths"])
    assert "~/.codex/auth.json" in blocked
    assert "~/.claude" in blocked
    assert "~/Library/Keychains" in blocked
    assert ".env" in blocked
    assert "secrets" in blocked


def test_default_commands_are_non_provider_only() -> None:
    commands = _contract()["authorization"]["default_commands"]
    assert commands
    for command in commands:
        assert command["provider_call"] is False
        assert command["cost_bearing"] is False

    planned = _contract()["authorization"]["planned_provider_commands"]
    assert planned
    for command in planned:
        assert command["provider_call"] is True
        assert command["cost_bearing"] is True
        assert command["requires_human_approval"] is True


def test_audit_and_redaction_are_required() -> None:
    data = _contract()
    assert data["redaction"]["required"] is True
    assert data["audit"]["required"] is True
    required = set(data["audit"]["required_fields"])
    assert {"timestamp", "request_id", "task_id", "command_id", "approval_id", "redaction_count"} <= required


def test_docs_reference_contract_and_no_runtime_claim() -> None:
    for path in (ADR, ARCH, MANUAL):
        text = path.read_text()
        assert "manifests/host-cli-bridge-contract.yaml" in text
    assert "design-only" in MANUAL.read_text()
    assert "The bridge is not a shell" in ARCH.read_text()
