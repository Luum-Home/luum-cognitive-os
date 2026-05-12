"""Contract tests for public runtime environment flags."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "runtime-env-flags.yaml"
DOC = REPO / "docs" / "runtime-env-flags.md"
ENV_EXAMPLE = REPO / "env.example"


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_runtime_env_flags_manifest_shape() -> None:
    data = _manifest()
    assert data["schema_version"] == "runtime-env-flags.v1"
    assert data["flags"], "runtime env flag manifest must not be empty"
    required = set(data["required_flag_fields"])
    for flag in data["flags"]:
        missing = required - set(flag)
        assert not missing, f"{flag.get('name')} missing fields: {sorted(missing)}"
        assert flag["family"] in data["families"], flag["name"]
        assert flag["risk_level"] in data["risk_levels"], flag["name"]
        assert isinstance(flag["owner_files"], list) and flag["owner_files"], flag["name"]
        assert isinstance(flag["documentation"], list) and flag["documentation"], flag["name"]
        assert isinstance(flag["bypasses_safety_primitive"], bool), flag["name"]


def test_core_runtime_flag_families_are_registered() -> None:
    data = _manifest()
    families = {flag["family"] for flag in data["flags"]}
    for family in {
        "hook-suppression",
        "llm-dispatch",
        "startup-safe-mode",
        "test-opt-in",
        "safety-bypass",
        "optional-service",
        "watchdog-observability",
        "secret-loading",
    }:
        assert family in families


def test_cos_skip_dotenv_is_public_contract() -> None:
    data = _manifest()
    by_name = {flag["name"]: flag for flag in data["flags"]}
    flag = by_name["COS_SKIP_DOTENV"]
    assert flag["family"] == "secret-loading"
    assert flag["default"] == "0"
    assert flag["risk_level"] == "medium"
    assert flag["bypasses_safety_primitive"] is False
    assert "scripts/smoke-qwen-fallback.sh" in flag["owner_files"]
    assert "lib/qwen_provider.py" in flag["owner_files"]


def test_cos_codex_exec_model_is_public_provider_smoke_contract() -> None:
    data = _manifest()
    by_name = {flag["name"]: flag for flag in data["flags"]}
    flag = by_name["COS_CODEX_EXEC_MODEL"]
    assert flag["family"] == "test-opt-in"
    assert flag["default"] == "unset"
    assert flag["risk_level"] == "medium"
    assert flag["bypasses_safety_primitive"] is False
    assert "scripts/cos_service_control_plane.py" in flag["owner_files"]
    assert "scripts/cos-headless-service-drill" in flag["owner_files"]
    assert "docs/09-Quality/manual-tests/headless-docker-service-runtime.md" in flag["documentation"]


def test_runtime_env_flags_doc_links_manifest_and_cos_skip_dotenv() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "manifests/runtime-env-flags.yaml" in text
    assert "COS_SKIP_DOTENV" in text
    assert "COS_CODEX_EXEC_MODEL" in text
    assert "secret-loading" in text


def test_public_runtime_flags_are_represented_in_env_example() -> None:
    data = _manifest()
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for flag in data["flags"]:
        name = flag["name"]
        if name.endswith("*"):
            assert name.rstrip("*") in text, name
        else:
            assert name in text, name


def test_provider_credential_gaps_are_represented_in_env_example() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for name in {"CODEX_API_KEY", "ANTHROPIC_AUTH_TOKEN", "COGNEE_API_KEY"}:
        assert name in text
