from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_SCHEMA = REPO_ROOT / "manifests" / "service-control-plane-schema.yaml"
EXECUTOR_CONTRACTS = REPO_ROOT / "manifests" / "provider-executor-contracts.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_service_control_plane_schema_declares_required_surfaces() -> None:
    schema = _load(SERVICE_SCHEMA)

    assert schema["schema_version"] == "service-control-plane.v1"
    assert schema["status"] == "phase1_local_proof"
    assert set(schema["required_surfaces"]) == {
        "cosd",
        "task_queue",
        "scheduler",
        "lease_manager",
        "worker",
        "executor_adapter",
        "engram_cloud",
        "artifact_store",
        "propose_only_publication",
    }
    assert set(schema["required_surfaces"]).issubset(schema["surfaces"])


def test_service_control_plane_keeps_publication_propose_only() -> None:
    schema = _load(SERVICE_SCHEMA)
    publication = schema["surfaces"]["propose_only_publication"]

    assert publication["human_approval_required"] is True
    assert "draft_pr" in publication["allowed_outputs"]
    assert "evidence_bundle" in publication["allowed_outputs"]
    for blocked in ["auto_merge", "direct_main_push", "force_push", "publish_credentials"]:
        assert blocked in publication["blocked_actions"]

    cosd = schema["surfaces"]["cosd"]
    assert "read_provider_credential_stores" in cosd["must_not"]
    assert "copy_provider_tokens" in cosd["must_not"]


def test_service_control_plane_phase_order_prevents_provider_first_build() -> None:
    schema = _load(SERVICE_SCHEMA)
    phases = schema["phase_order"]

    assert phases.index("contract") < phases.index("local_queue")
    assert phases.index("local_queue") < phases.index("local_worker")
    assert phases.index("local_worker") < phases.index("host_cli_executor")
    assert phases.index("host_cli_executor") < phases.index("container_cli_executor")

    local_worker = schema["phase_gates"]["local_worker"]
    assert local_worker["required_executor"] == "local-command"
    assert local_worker["no_provider_credentials"] is True
    assert schema["phase_gates"]["crash_resume"]["implementation_status"] == "implemented_for_expired_lease_resume"
    assert schema["phase_gates"]["host_cli_executor"]["implementation_status"] == "dry_run_adapter_implemented"


def test_service_control_plane_runtime_shapes_separate_maintainer_and_hosted_credentials() -> None:
    schema = _load(SERVICE_SCHEMA)
    local = schema["runtime_shapes"]["local_maintainer_host"]
    hosted = schema["runtime_shapes"]["ci_or_hosted_cloud"]

    assert local["default_cost_posture"] == "subscription_account"
    assert local["preferred_credential_modes"] == ["account-session"]
    assert "host" in local["allowed_runtimes"]

    assert hosted["default_cost_posture"] == "api_metered"
    assert "api-key" in hosted["preferred_credential_modes"]
    assert "provider-cloud" in hosted["preferred_credential_modes"]
    assert "cloud" in hosted["allowed_runtimes"]


def test_provider_executor_registry_declares_credential_and_cost_enums() -> None:
    registry = _load(EXECUTOR_CONTRACTS)

    assert registry["schema_version"] == "provider-executor-contracts.v1"
    enums = registry["enums"]
    assert {"account-session", "device-login", "api-key", "provider-cloud", "proxy-gateway"}.issubset(
        enums["credential_modes"]
    )
    assert {"subscription_account", "api_metered", "provider_cloud_metered", "gateway_metered"}.issubset(
        enums["cost_modes"]
    )
    assert set(enums["auth_probe_statuses"]) == {"ready", "auth_required", "unsupported", "unsafe"}


def test_provider_executor_adapters_have_required_fields_and_safe_probe_statuses() -> None:
    registry = _load(EXECUTOR_CONTRACTS)
    required = set(registry["required_adapter_fields"])
    allowed_statuses = set(registry["enums"]["auth_probe_statuses"])
    allowed_credentials = set(registry["enums"]["credential_modes"])
    allowed_costs = set(registry["enums"]["cost_modes"])
    allowed_runtimes = set(registry["enums"]["allowed_runtimes"])

    for adapter in registry["adapters"]:
        missing = required - set(adapter)
        assert not missing, f"{adapter.get('executor_id')} missing {sorted(missing)}"
        assert set(adapter["auth_probe"]["expected_statuses"]).issubset(allowed_statuses)
        assert set(adapter["credential_modes"]).issubset(allowed_credentials)
        assert adapter["cost_mode"] in allowed_costs
        assert set(adapter["allowed_runtimes"]).issubset(allowed_runtimes)
        assert adapter["propose_only_required"] is True
        assert adapter["credential_store_access"] != "raw_read_allowed"


def test_provider_executor_registry_starts_with_local_command_before_model_providers() -> None:
    registry = _load(EXECUTOR_CONTRACTS)
    adapters = {adapter["executor_id"]: adapter for adapter in registry["adapters"]}

    local = adapters["local-command"]
    assert local["credential_modes"] == ["none"]
    assert local["cost_mode"] == "none"
    assert local["lifecycle_state"] == "sandbox"

    for executor_id in ["codex-cli-host", "claude-cli-host"]:
        adapter = adapters[executor_id]
        assert adapter["runtime_kind"] == "official_cli_host"
        assert adapter["lifecycle_state"] == "sandbox"
        assert "account-session" in adapter["credential_modes"]
        assert adapter["cost_mode"] == "subscription_account"
        assert adapter["allowed_runtimes"] == ["host"]

    for executor_id in ["codex-cli-container", "claude-cli-container"]:
        adapter = adapters[executor_id]
        assert adapter["runtime_kind"] == "official_cli_container"
        assert adapter["allowed_runtimes"] == ["container"]
        assert adapter["credential_store_access"] == "documented_provider_mount_only"


def test_lab_only_provider_placeholders_do_not_claim_runtime_support() -> None:
    registry = _load(EXECUTOR_CONTRACTS)
    placeholders = {entry["provider"] for entry in registry["lab_only_provider_placeholders"]}
    adapter_providers = {entry["provider"] for entry in registry["adapters"]}

    assert placeholders == {"kimi", "minimax", "deepseek"}
    assert placeholders.isdisjoint(adapter_providers)
