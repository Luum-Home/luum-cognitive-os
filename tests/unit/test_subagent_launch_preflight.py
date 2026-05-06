from pathlib import Path

import pytest

from scripts.subagent_launch_preflight import evaluate, load_manifest


REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "subagent-capabilities.yaml"


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(MANIFEST)


def test_explore_blocks_file_artifact_requirement(manifest):
    result = evaluate(
        "Explore",
        "Research this and write to .cognitive-os/strategy/research/02-real-self-improvement.md",
        manifest,
    )

    assert result.status == "block"
    assert result.classification == "capability_contract_mismatch"
    assert result.prompt_requires_write is True
    assert result.write_capability is False
    assert "general-purpose" in result.safe_alternatives
    assert result.exit_code == 2


def test_explore_allows_result_only_without_artifact_requirement(manifest):
    result = evaluate(
        "Explore",
        "Inspect the router code and return findings in result only.",
        manifest,
    )

    assert result.status == "pass"
    assert result.classification == "compatible_launch"
    assert result.prompt_requires_write is False
    assert result.write_capability is False


def test_explore_allows_explicit_parent_persistence(manifest):
    result = evaluate(
        "Explore",
        "Explore read-only and return result only; parent will persist artifacts to research/02.md",
        manifest,
    )

    assert result.status == "pass"
    assert result.classification == "parent_persistence_declared"
    assert result.prompt_requires_write is True
    assert result.parent_persistence_declared is True
    assert result.write_capability is False


def test_general_purpose_allows_file_artifact_requirement(manifest):
    result = evaluate(
        "general-purpose",
        "Research this and write docs/reports/output.md",
        manifest,
    )

    assert result.status == "pass"
    assert result.classification == "compatible_launch"
    assert result.prompt_requires_write is True
    assert result.write_capability is True


def test_worker_allows_spanish_file_artifact_requirement(manifest):
    result = evaluate(
        "worker",
        "Investigá y guardá en research/03-private-content.md",
        manifest,
    )

    assert result.status == "pass"
    assert result.prompt_requires_write is True
    assert result.write_capability is True


def test_unknown_type_blocks(manifest):
    result = evaluate("mystery", "inspect the code", manifest)

    assert result.status == "block"
    assert result.classification == "unknown_subagent_type"
    assert result.write_capability is None
