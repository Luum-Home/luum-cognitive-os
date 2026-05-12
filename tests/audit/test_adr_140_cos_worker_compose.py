from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker" / "cos-worker" / "docker-compose.yml"
DOCKERFILE = ROOT / "docker" / "cos-worker" / "Dockerfile"
ENTRYPOINT = ROOT / "docker" / "cos-worker" / "entrypoint.sh"
BOOTSTRAP = ROOT / "scripts" / "cos-cloud-worker-bootstrap.sh"
ADR = ROOT / "docs" / "02-Decisions" / "adrs" / "ADR-140-cross-os-containerized-deployment.md"
PORTABILITY = ROOT / "docs" / "04-Concepts" / "architecture" / "bootstrap-portability.md"


def _compose_payload() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_adr_140_worker_surface_files_exist() -> None:
    for path in (COMPOSE, DOCKERFILE, ENTRYPOINT, BOOTSTRAP):
        assert path.exists(), f"missing ADR-140 worker surface file: {path.relative_to(ROOT)}"


def test_compose_declares_worker_and_optional_engram_profile() -> None:
    payload = _compose_payload()
    services = payload["services"]

    worker = services["cos-worker"]
    assert worker["build"]["dockerfile"] == "docker/cos-worker/Dockerfile"
    assert worker["working_dir"] == "/workspace"
    assert worker["command"] == ["--self-test"]
    assert any(str(volume).endswith(":/workspace") for volume in worker["volumes"])
    assert worker["environment"]["COGNITIVE_OS_PROJECT_DIR"] == "/workspace"
    assert worker["environment"]["COGNITIVE_OS_HARNESS"] == "barecli"

    proxy = services["cos-engram-proxy"]
    assert "engram-cloud" in proxy.get("profiles", [])


def test_compose_uses_account_agnostic_provider_env_names() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    blocked_vendor_tokens = ("ANTHROPIC", "OPENAI", "CLAUDE", "QWEN", "DEEPSEEK", "CODEX")

    for token in blocked_vendor_tokens:
        assert token not in text, f"ADR-140 compose surface must not expose vendor-specific env var: {token}"

    assert "LLM_PRIMARY_API_KEY" in text
    assert "LLM_FALLBACK_API_KEY" in text


def test_worker_image_has_no_shell_profile_or_home_directory_assumption() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    entrypoint = ENTRYPOINT.read_text(encoding="utf-8")

    assert "FROM python:3.11-slim" in dockerfile
    assert "~/.claude" not in dockerfile
    assert "~/.engram" not in dockerfile
    assert "~/.claude" not in entrypoint
    assert "~/.engram" not in entrypoint
    assert "/workspace/.cognitive-os/runtime" in dockerfile
    assert "agent-audit-trail.jsonl" in entrypoint
    assert "git-commit-scope-guard.sh" in entrypoint


def test_bootstrap_wrapper_is_thin_compose_entrypoint() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")

    assert "docker compose -f" in text
    assert "cos-worker" in text
    assert "COS_WORKSPACE" in text
    assert "~/.claude" not in text
    assert "~/.engram" not in text


def test_adr_140_and_bootstrap_portability_record_implementation_evidence() -> None:
    adr = ADR.read_text(encoding="utf-8")
    portability = PORTABILITY.read_text(encoding="utf-8")

    assert "Accepted — Implemented" in adr
    assert "`docker/cos-worker/docker-compose.yml`" in adr
    assert "`scripts/cos-cloud-worker-bootstrap.sh`" in adr
    assert "ADR-140 container worker surface" in portability
    assert "docker/cos-worker/docker-compose.yml" in portability
