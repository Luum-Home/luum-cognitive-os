"""Contract tests preventing ADR-126/127 lifecycle metadata from becoming aspirational."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "manifests" / "primitive-lifecycle.yaml"
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
HOOK_RE = re.compile(r"hooks/[A-Za-z0-9_.-]+\.sh")
INACTIVE_STATES = {"demoted", "archived", "deleted"}


def _projected_hooks() -> set[str]:
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    hooks: set[str] = set()
    for matchers in data.get("hooks", {}).values():
        if not isinstance(matchers, list):
            continue
        for matcher in matchers:
            for hook_def in matcher.get("hooks", []) if isinstance(matcher, dict) else []:
                if isinstance(hook_def, dict):
                    hooks.update(HOOK_RE.findall(str(hook_def.get("command", ""))))
    return hooks


def _manifest_primitives() -> list[dict[str, object]]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return data["primitives"]


def _hook_text(hook_path: str) -> str:
    return (REPO_ROOT / hook_path).read_text(encoding="utf-8", errors="ignore")


def test_every_projected_hook_has_lifecycle_metadata() -> None:
    projected = _projected_hooks()
    manifest_hooks = {str(item["id"]) for item in _manifest_primitives() if str(item.get("id", "")).startswith("hooks/")}

    assert projected - manifest_hooks == set()


def test_runtime_projected_hook_metadata_points_to_existing_hooks() -> None:
    missing: list[str] = []
    for item in _manifest_primitives():
        if item.get("kind") != "hook" or not item.get("runtime_projection"):
            continue
        hook_path = str(item["id"])
        if not (REPO_ROOT / hook_path).exists():
            missing.append(hook_path)
    assert missing == []


def test_blocking_maturity_matches_real_exit2_behavior_and_tests() -> None:
    offenders: list[str] = []
    for item in _manifest_primitives():
        if item.get("kind") != "hook" or item.get("maturity") != "blocking":
            continue
        hook_path = str(item["id"])
        evidence = [str(command) for command in item.get("evidence_commands", [])]
        has_test_evidence = any("pytest" in command and "test" in command for command in evidence)
        if "exit 2" not in _hook_text(hook_path) or not has_test_evidence:
            offenders.append(hook_path)
    assert offenders == []


def test_non_blocking_metadata_does_not_claim_blocking_lifecycle() -> None:
    offenders = [
        str(item["id"])
        for item in _manifest_primitives()
        if item.get("maturity") != "blocking" and item.get("lifecycle_state") in {"blocking", "default-on"}
    ]
    assert offenders == []


def test_runtime_projected_hooks_are_not_deleted_or_archived() -> None:
    offenders = [
        str(item["id"])
        for item in _manifest_primitives()
        if item.get("kind") == "hook" and item.get("runtime_projection") and item.get("lifecycle_state") in INACTIVE_STATES
    ]
    assert offenders == []
