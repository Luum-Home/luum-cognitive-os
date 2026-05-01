"""Contracts for keeping Anthropic direct API out of default/local surfaces."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = [pytest.mark.unit]


def test_env_example_does_not_define_uncommented_anthropic_key() -> None:
    text = (PROJECT_ROOT / "env.example").read_text()
    active_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert "ANTHROPIC_API_KEY=" not in active_lines


def test_bootstrap_does_not_tell_users_to_set_anthropic_key() -> None:
    text = (PROJECT_ROOT / "scripts" / "cos-bootstrap.sh").read_text()
    assert "Set ANTHROPIC_API_KEY" not in text


def test_cognee_reference_container_defaults_to_local_provider() -> None:
    text = (PROJECT_ROOT / "docker-compose.cognitive-os.yml").read_text()
    cognee_block = text.split("  cognee:", 1)[1].split(
        "  # ---------------------------------------------------------------------------",
        1,
    )[0]
    assert "ANTHROPIC_API_KEY" not in cognee_block
    assert "COGNEE_LLM_PROVIDER:-ollama" in cognee_block
    assert "EMBEDDING_PROVIDER" in cognee_block


def test_cognee_skill_defaults_to_local_provider() -> None:
    text = (
        PROJECT_ROOT
        / "packages"
        / "ecosystem-tools"
        / "skills"
        / "cognee-integration"
        / "SKILL.md"
    ).read_text()
    assert "COGNEE_LLM_PROVIDER:-anthropic" not in text
    assert "COGNEE_LLM_PROVIDER=ollama" in text


def test_advisory_llm_package_has_no_anthropic_env_gate() -> None:
    package = yaml.safe_load(
        (PROJECT_ROOT / "packages" / "cos-advisory-llm" / "cos-package.yaml").read_text()
    )
    assert package.get("dependencies") == {}
    registrations = package.get("hook_registrations", [])
    assert registrations
    for registration in registrations:
        assert registration.get("requires_env") in (None, [])
        assert registration.get("skip_if_missing") is False


def test_llm_status_treats_key_alone_as_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
    module_path = PROJECT_ROOT / "scripts" / "llm_status.py"
    spec = importlib.util.spec_from_file_location("llm_status_for_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    configured = module._provider_configured()["anthropic_api_direct"]
    assert configured["configured"] is False
    assert configured["policy_enabled"] is False
