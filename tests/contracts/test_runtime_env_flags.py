from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "runtime-env-flags.yaml"
DOC = REPO / "docs" / "runtime-env-flags.md"
ENV_EXAMPLE = REPO / "env.example"


def test_cos_codex_exec_model_runtime_flag_contract() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    by_name = {flag["name"]: flag for flag in data["flags"]}
    flag = by_name["COS_CODEX_EXEC_MODEL"]
    assert flag["family"] == "test-opt-in"
    assert flag["default"] == "unset"
    assert flag["risk_level"] == "medium"
    assert flag["bypasses_safety_primitive"] is False
    assert "scripts/cos_service_control_plane.py" in flag["owner_files"]
    assert "scripts/cos-headless-service-drill" in flag["owner_files"]
    assert "docs/manual-tests/headless-docker-service-runtime.md" in flag["documentation"]
    assert "COS_CODEX_EXEC_MODEL" in DOC.read_text(encoding="utf-8")
    assert "COS_CODEX_EXEC_MODEL" in ENV_EXAMPLE.read_text(encoding="utf-8")


def test_cos_claude_provider_smoke_runtime_flags_contract() -> None:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    by_name = {flag["name"]: flag for flag in data["flags"]}
    for name in {"COS_CLAUDE_EXEC_MODEL", "COS_CLAUDE_BIN"}:
        flag = by_name[name]
        assert flag["family"] == "test-opt-in"
        assert flag["default"] == "unset"
        assert flag["risk_level"] == "medium"
        assert flag["bypasses_safety_primitive"] is False
        assert "scripts/cos_service_control_plane.py" in flag["owner_files"]
        assert name in DOC.read_text(encoding="utf-8")
        assert name in ENV_EXAMPLE.read_text(encoding="utf-8")
