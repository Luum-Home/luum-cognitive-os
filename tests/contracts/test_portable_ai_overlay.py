"""ADR-258 portable `.ai` overlay contract tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERLAY = REPO_ROOT / ".ai"
REQUIRED_CONTRACT_IDS = {
    "destructive-git-blocker",
    "destructive-rm-blocker",
    "reinvention-check",
    "large-file-advisor",
    "skill-router",
}
STRUCTURAL_ONLY = {"cursor", "vscode-copilot"}


def _json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _contracts() -> list[dict[str, Any]]:
    data = yaml.safe_load((REPO_ROOT / "manifests" / "primitive-contracts.yaml").read_text(encoding="utf-8"))
    return list(data["contracts"])


def _lifecycle_count() -> int:
    data = yaml.safe_load((REPO_ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    return len(data["primitives"])


def _primitive_files() -> list[Path]:
    return sorted((OVERLAY / "primitives").glob("**/*.json"))


def test_portable_ai_overlay_is_generated_and_current() -> None:
    result = subprocess.run(
        ["python3", "scripts/portable_ai_overlay.py", "--check"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_context_records_generated_noncanonical_overlay() -> None:
    context = _json(OVERLAY / "context.json")
    assert context["schema_version"] == "portable-ai-context.v1"
    assert context["status"] == "generated-portable-overlay"
    assert context["native_file_emission"] is False
    assert "future adapter compiler" in context["consumer_package_policy"]
    assert "scripts/cos_init.py" in context["native_projection_drivers"]
    assert "manifests/primitive-contracts.yaml" in context["canonical_source_of_truth"]
    assert "manifests/primitive-lifecycle.yaml" in context["canonical_source_of_truth"]
    assert context["primitive_count"] >= _lifecycle_count()
    assert context["policy"].startswith("The `.ai` tree is a generated maintainer overlay")


def test_all_lifecycle_primitives_have_ai_overlay_rows() -> None:
    primitive_files = _primitive_files()
    assert len(primitive_files) >= _lifecycle_count()
    rows = [_json(path) for path in primitive_files]
    source_ids = {row["source_id"] for row in rows}
    lifecycle = yaml.safe_load((REPO_ROOT / "manifests" / "primitive-lifecycle.yaml").read_text(encoding="utf-8"))
    expected = {item["id"] for item in lifecycle["primitives"]}
    assert expected <= source_ids
    assert all(row["canonical_source_kind"] == "cos-internal" for row in rows)
    assert all(row["overlay_role"] == "generated-reference" for row in rows)


def test_contract_slice_round_trips_into_ai_primitives() -> None:
    rows = [_json(path) for path in _primitive_files()]
    by_contract = {row["contract"]["contract_id"]: row for row in rows if row["contract"]["present"]}
    assert REQUIRED_CONTRACT_IDS <= set(by_contract)
    for contract in _contracts():
        row = by_contract[contract["id"]]
        assert row["portable_id"] == contract["id"]
        assert row["canonical_source"] == contract["source"]
        assert row["contract"]["intent"] == contract["intent"]
        assert row["contract"]["requires"] == contract["requires"]
        assert set(row["contract"]["projection_fidelity"]) == set(contract["projection"])


def test_profiles_do_not_overclaim_structural_advisory_enforcement() -> None:
    for harness in STRUCTURAL_ONLY:
        profile = _json(OVERLAY / "profiles" / f"{harness}.json")
        assert profile["schema_version"] == "portable-ai-profile.v1"
        assert profile["proof_level"] == "structural"
        for row in profile["contract_projection_fidelity"]:
            assert row["fidelity"] == "structural-advisory"
            assert row["claims_runtime_enforcement"] is False


def test_adapter_manifests_are_declarative_and_do_not_emit_native_files() -> None:
    for manifest_path in (OVERLAY / "adapters").glob("*/adapter.json"):
        manifest = _json(manifest_path)
        assert manifest["adapter_contract_kind"] == "declarative-manifest"
        assert manifest["native_file_emission"] is False
        assert "projection_fidelity" in manifest["compiler_gap_policy"]
        for row in manifest["projected_primitives"]:
            if row["fidelity"] == "structural-advisory":
                assert row["claims_runtime_enforcement"] is False


def test_profiles_record_compiler_gap_policy() -> None:
    for profile_path in (OVERLAY / "profiles").glob("*.json"):
        profile = _json(profile_path)
        assert profile["adapter_contract_kind"] == "declarative-fidelity-profile"
        assert profile["native_file_emission"] is False
        assert "future adapter compiler" in profile["compiler_gap_policy"]


def test_adapters_and_privacy_schemas_exist() -> None:
    for path in [
        OVERLAY / "adapters" / "claude-code" / "README.md",
        OVERLAY / "adapters" / "codex" / "README.md",
        OVERLAY / "adapters" / "cursor" / "README.md",
        OVERLAY / "adapters" / "opencode" / "README.md",
        OVERLAY / "logs" / "schema" / "primitive-interventions.schema.json",
        OVERLAY / "logs" / "schema" / "codebase-itinerary.schema.json",
    ]:
        assert path.exists(), path
