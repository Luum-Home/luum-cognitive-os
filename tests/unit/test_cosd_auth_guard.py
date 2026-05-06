from __future__ import annotations

from lib.cosd_auth_guard import inspect_command, inspect_payload


def test_remote_cosd_serve_requires_allow_remote() -> None:
    finding = inspect_command("scripts/cosd serve --host 0.0.0.0 --port 8765")
    assert finding is not None
    assert "--allow-remote" in finding.reason


def test_remote_cosd_serve_requires_token_auth(monkeypatch) -> None:
    monkeypatch.delenv("COSD_API_TOKEN_FILE", raising=False)
    finding = inspect_command("scripts/cosd serve --host 0.0.0.0 --allow-remote")
    assert finding is not None
    assert "token" in finding.reason


def test_remote_cosd_serve_with_token_file_allowed() -> None:
    finding = inspect_command(
        "python3 scripts/cos_daemon.py serve --host 0.0.0.0 --allow-remote --token-file /run/cosd/token"
    )
    assert finding is None


def test_local_cosd_serve_allowed_without_token() -> None:
    assert inspect_command("scripts/cosd serve --host 127.0.0.1 --port 8765") is None


def test_cosd_config_edit_requires_approval(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COS_ALLOW_COSD_AUTH_CONFIG_WRITE", raising=False)
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "infra/cosd/k8s/cosd-local.yaml"}}
    findings = inspect_payload(payload, project_dir=tmp_path)
    assert findings
    assert "approval" in findings[0].reason


def test_cosd_config_edit_allows_explicit_approval(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COS_ALLOW_COSD_AUTH_CONFIG_WRITE", "1")
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "infra/cosd/k8s/cosd-local.yaml"}}
    assert inspect_payload(payload, project_dir=tmp_path) == []
