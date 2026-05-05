from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "manifests" / "proof-drill-registry.yaml"
OPT_IN_CLASSES = {"smoke-opt-in", "proof-drill", "manual-proof"}
REQUIRED_ENTRIES = {
    "os-pytest-summary",
    "consumer-project-run-tests",
    "os-smoke-test-skill",
    "qwen-fallback-live-smoke",
    "multi-provider-fallback-live-smoke",
    "headless-docker-service-drill",
    "engram-cloud-docker-smoke",
    "cross-instance-learning-drill",
    "service-control-plane-manual-proof",
    "test-contract-repair",
}
REQUIRED_FIELDS = {
    "id",
    "class",
    "scope",
    "primitive_kind",
    "selector",
    "default_lane",
    "cost_class",
    "requires_credentials",
    "destructive_scope",
    "docs",
    "automated_checks",
    "when_to_run",
    "proves",
    "does_not_prove",
}


def _registry() -> dict:
    return yaml.safe_load(REGISTRY.read_text())


def _entries() -> list[dict]:
    return _registry()["entries"]


def test_registry_has_required_entries_and_schema() -> None:
    registry = _registry()
    assert registry["schema_version"] == "proof-drill-registry.v1"
    assert set(registry["required_entry_fields"]) == REQUIRED_FIELDS

    ids = {entry["id"] for entry in registry["entries"]}
    assert REQUIRED_ENTRIES <= ids

    for entry in registry["entries"]:
        assert REQUIRED_FIELDS <= set(entry), entry["id"]
        assert entry["class"] in registry["classes"], entry["id"]
        assert entry["scope"] in registry["scopes"], entry["id"]
        assert entry["primitive_kind"] in {"skill", "script", "documentation"}, entry["id"]
        assert isinstance(entry["docs"], list) and entry["docs"], entry["id"]
        assert isinstance(entry["automated_checks"], list), entry["id"]
        assert entry["proves"], entry["id"]
        assert entry["does_not_prove"], entry["id"]


def test_selectors_docs_and_automated_checks_resolve() -> None:
    for entry in _entries():
        selector = REPO_ROOT / entry["selector"]
        assert selector.exists(), f"missing selector for {entry['id']}: {entry['selector']}"

        for doc in entry["docs"]:
            assert (REPO_ROOT / doc).exists(), f"missing doc for {entry['id']}: {doc}"

        for check in entry["automated_checks"]:
            assert (REPO_ROOT / check).exists(), f"missing check for {entry['id']}: {check}"


def test_opt_in_rows_never_enter_default_lanes() -> None:
    for entry in _entries():
        if entry["class"] in OPT_IN_CLASSES:
            assert entry["default_lane"] is False, entry["id"]


def test_provider_and_docker_checks_are_explicit_opt_ins() -> None:
    costly_markers = ("provider", "docker", "cloud", "kubernetes", "vm")
    for entry in _entries():
        cost_class = str(entry["cost_class"]).lower()
        if any(marker in cost_class for marker in costly_markers):
            assert entry["class"] in OPT_IN_CLASSES, entry["id"]
            assert entry["default_lane"] is False, entry["id"]


def test_consumer_project_boundary_is_represented() -> None:
    consumer_rows = [entry for entry in _entries() if entry["scope"] == "consumer-project"]
    assert consumer_rows
    assert any(row["id"] == "consumer-project-run-tests" for row in consumer_rows)
    for row in consumer_rows:
        assert not str(row["selector"]).startswith("scripts/smoke-"), row["id"]
        assert not str(row["selector"]).startswith("scripts/cos-headless"), row["id"]


def test_registry_policy_declares_evidence_and_provider_skip_rules() -> None:
    policy = _registry()["policy"]
    assert set(policy["opt_in_classes"]) == OPT_IN_CLASSES
    assert "must never" in policy["default_lane_rule"]
    assert "Consumer projects" in policy["consumer_boundary"]
    assert "what it does not prove" in policy["evidence_rule"]
    assert "SKIPPED" in policy["provider_rule"]
