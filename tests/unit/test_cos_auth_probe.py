from __future__ import annotations

import os
from pathlib import Path

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import cos_auth_probe as probe  # noqa: E402


def test_local_probe_is_ready_without_credentials() -> None:
    result = probe.probe("local", "none", env={}, path="")

    assert result.status == "ready"
    assert result.credential_store_access == "none"
    assert result.cost_mode == "none"


def test_codex_api_key_probe_uses_environment_only() -> None:
    missing = probe.probe("codex", "api-key", env={}, path="")
    present = probe.probe("codex", "api-key", env={"OPENAI_API_KEY": "sk-test-value"}, path="")

    assert missing.status == "auth_required"
    assert present.status == "ready"
    assert present.credential_store_access == "none"


def test_claude_oauth_probe_uses_environment_only() -> None:
    missing = probe.probe("claude", "oauth-token", env={}, path="")
    present = probe.probe("claude", "oauth-token", env={"ANTHROPIC_AUTH_TOKEN": "token"}, path="")

    assert missing.status == "auth_required"
    assert present.status == "ready"
    assert present.credential_store_access == "none"


def test_missing_cli_account_session_is_unsupported() -> None:
    result = probe.probe("codex", "account-session", env={}, path="")

    assert result.status == "unsupported"
    assert "not found" in result.reason
    assert result.credential_store_access == "forbidden"


def test_fake_codex_login_status_can_report_ready(tmp_path: Path) -> None:
    fake = tmp_path / "codex"
    fake.write_text("#!/bin/sh\necho 'Logged in using ChatGPT'\n", encoding="utf-8")
    fake.chmod(0o755)

    result = probe.probe("codex", "account-session", env={"PATH": str(tmp_path)}, path=str(tmp_path))

    assert result.status == "ready"
    assert result.command == "codex login status"
    assert result.credential_store_access == "forbidden"


def test_cli_wrapper_json_does_not_require_real_provider(tmp_path: Path) -> None:
    output = os.popen(f"{REPO_ROOT / 'scripts' / 'cos-auth-probe'} --provider local --mode none --json").read()

    assert '"status": "ready"' in output


def test_fake_claude_auth_status_can_report_ready(tmp_path: Path) -> None:
    fake = tmp_path / "claude"
    fake.write_text("#!/bin/sh\nif [ \"$1 $2\" = \"auth status\" ]; then echo '{\"loggedIn\": true}'; exit 0; fi\necho '2.1.62 (Claude Code)'\n", encoding="utf-8")
    fake.chmod(0o755)

    result = probe.probe("claude", "account-session", env={"PATH": str(tmp_path)}, path=str(tmp_path))

    assert result.status == "ready"
    assert result.command == "claude auth status"
    assert result.credential_store_access == "forbidden"


def test_claude_known_local_bin_is_discovered_when_not_on_path(tmp_path: Path, monkeypatch) -> None:
    local_bin = tmp_path / ".local" / "bin"
    local_bin.mkdir(parents=True)
    fake = local_bin / "claude"
    fake.write_text("#!/bin/sh\nif [ \"$1 $2\" = \"auth status\" ]; then echo '{\"loggedIn\": true}'; exit 0; fi\necho '2.1.62 (Claude Code)'\n", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("HOME", str(tmp_path))

    result = probe.probe("claude", "account-session", env={"PATH": ""}, path="")

    assert result.status == "ready"
    assert result.command == "claude auth status"
