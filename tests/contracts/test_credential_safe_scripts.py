"""Contract tests for credential-safe script allowlist."""

from __future__ import annotations

from pathlib import Path
import hashlib

import yaml

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "manifests" / "credential-safe-scripts.yaml"
DOC = REPO / "docs" / "manual-tests" / "credential-safe-script-runner.md"


def _manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_shape_and_invariants() -> None:
    data = _manifest()
    assert data["schema_version"] == "credential-safe-scripts.v1"
    required = set(data["required_script_fields"])
    assert data["scripts"]
    for entry in data["scripts"]:
        assert not (required - set(entry)), entry.get("id")
        assert entry["requires_explicit_approval"] is True
        assert entry["risk_level"] in {"medium", "high"}
        assert isinstance(entry["command"], list) and entry["command"]
        assert set(entry["command_integrity"]) == {"path", "sha256"}
        assert len(entry["command_integrity"]["sha256"]) == 64
        assert isinstance(entry["allowed_env_keys"], list)
        assert entry["allowed_env_files"] == [".env"]
        assert isinstance(entry["inherited_env_keys"], list)
        assert isinstance(entry["forced_env"], dict)
        assert "audit_log" in entry
    for invariant in {
        "no_arbitrary_commands",
        "pinned_command_integrity",
        "no_shell_eval_of_env_file",
        "allowlisted_env_keys_only",
        "allowlisted_env_files_only",
        "sanitized_child_environment",
        "bounded_model_visible_output",
        "redact_stdout_stderr_before_model_output",
        "explicit_operator_approval_required",
    }:
        assert invariant in data["invariants"]


def test_qwen_fallback_smoke_contract() -> None:
    scripts = {entry["id"]: entry for entry in _manifest()["scripts"]}
    entry = scripts["qwen-fallback-smoke"]
    assert entry["command"] == ["bash", "scripts/smoke-qwen-fallback.sh"]
    target = REPO / entry["command_integrity"]["path"]
    assert hashlib.sha256(target.read_bytes()).hexdigest() == entry["command_integrity"]["sha256"]
    assert entry["forced_env"]["COS_SKIP_DOTENV"] == "1"
    assert "ALIBABA_QWEN_API_KEY" in entry["allowed_env_keys"]
    assert "PATH" in entry["inherited_env_keys"]
    assert "OTHER_SECRET" in entry["blocked_env_keys"]
    assert entry["max_output_chars"] <= 20000


def test_manual_doc_mentions_redaction_and_allowlist() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "allowlisted" in text
    assert "redacts" in text or "redacted" in text
    assert "integrity" in text
    assert "qwen-fallback-smoke" in text
