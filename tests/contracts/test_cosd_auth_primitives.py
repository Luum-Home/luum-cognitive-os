from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from lib.cosd_auth_guard import inspect_command

ROOT = Path(__file__).resolve().parents[2]


def test_cosd_secure_rule_is_indexed_and_has_trigger() -> None:
    rule = ROOT / "rules" / "cosd-secure-api.md"
    text = rule.read_text(encoding="utf-8")
    assert "remote API" in text
    assert "Contextual Trigger" in text
    compact = (ROOT / "rules" / "RULES-COMPACT.md").read_text(encoding="utf-8")
    assert "[`cosd-secure-api`]" in compact


def test_cosd_auth_hook_is_registered_in_projection_surfaces() -> None:
    hook = "cosd-auth-guard.sh"
    assert hook in (ROOT / "hooks" / "_lib" / "registration-allowlist.txt").read_text(encoding="utf-8")
    assert hook in (ROOT / "scripts" / "_lib" / "settings-driver-claude-code.sh").read_text(encoding="utf-8")
    assert hook in (ROOT / "scripts" / "apply-efficiency-profile.sh").read_text(encoding="utf-8")
    for profile in (ROOT / "templates" / "security-profiles").glob("*.json"):
        data = json.loads(profile.read_text(encoding="utf-8"))
        assert hook in json.dumps(data)


def test_cosd_auth_primitive_evidence_manifest_entries_exist() -> None:
    evidence = yaml.safe_load((ROOT / "manifests" / "primitive-behavior-evidence.yaml").read_text(encoding="utf-8"))
    primitives = {row["primitive"] for row in evidence["evidence"]}
    assert "hooks/cosd-auth-guard.sh" in primitives
    assert "rules/cosd-secure-api.md" in primitives


def test_cosd_k8s_remote_bind_uses_allow_remote_and_token_file() -> None:
    text = (ROOT / "infra" / "cosd" / "k8s" / "cosd-local.yaml").read_text(encoding="utf-8")
    command_line = " ".join(re.findall(r'"([^"]+)"', text))
    assert "--host 0.0.0.0" in command_line
    assert "--allow-remote" in command_line
    assert "--token-file /run/cosd/token" in command_line
    assert "secretName: cosd-api-token" in text


def test_cosd_auth_policy_blocks_remote_bind_without_token() -> None:
    finding = inspect_command("python3 scripts/cos_daemon.py serve --host 0.0.0.0 --allow-remote")

    assert finding is not None
    assert finding.status == "FAIL"
    assert "token" in finding.reason
