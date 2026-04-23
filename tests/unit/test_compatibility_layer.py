"""Unit tests for lib/compatibility_layer.py."""

from pathlib import Path

import pytest

from lib.compatibility_layer import compatibility_inventory, compatibility_summary

pytestmark = pytest.mark.unit


def test_inventory_contains_expected_sections():
    inventory = compatibility_inventory()
    assert set(inventory) == {
        "providers",
        "harness_adapters",
        "documented_targets",
        "gateways",
        "tool_schemas",
    }


def test_all_declared_adapter_paths_exist():
    repo_root = Path(__file__).resolve().parents[2]
    inventory = compatibility_inventory()
    for section_name, section in inventory.items():
        for item in section:
            if "adapter_path" in item:
                path = repo_root / item["adapter_path"]
                assert path.exists(), f"Missing compatibility adapter path: {path}"
            if "evidence_path" in item:
                evidence = repo_root / item["evidence_path"]
                assert evidence.exists(), (
                    f"Missing compatibility evidence path in {section_name}: {evidence}"
                )


def test_documented_targets_include_opencode():
    inventory = compatibility_inventory()
    names = {item["name"] for item in inventory["documented_targets"]}
    assert "opencode" in names


def test_inventory_distinguishes_implemented_and_documented_surfaces():
    inventory = compatibility_inventory()
    provider_names = {item["name"] for item in inventory["providers"]}
    harness_names = {item["name"] for item in inventory["harness_adapters"]}
    documented_names = {item["name"] for item in inventory["documented_targets"]}

    assert {"claude", "codex", "gemini", "cursor", "windsurf"} <= provider_names
    assert {"claude_code", "aider"} <= harness_names
    assert {"opencode", "continue", "cline"} <= documented_names


def test_summary_mentions_provider_and_gateway_layers():
    summary = compatibility_summary()
    assert "Providers:" in summary
    assert "Harness adapters:" in summary
    assert "Documented targets:" in summary
    assert "Gateways:" in summary
    assert "Tool schemas:" in summary
