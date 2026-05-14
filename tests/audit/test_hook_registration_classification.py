"""Audit contract for intentionally unregistered top-level hooks.

After ADR-144, hooks excluded from live Claude projection must be classified as
future, conditional, manual, deprecated, demoted, or projected elsewhere. This
keeps the remaining hook debt explicit without enabling every hook by default.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.audit]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST = PROJECT_ROOT / "manifests" / "hook-registration-classification.yaml"
VALID_STATUSES = {
    "active",
    "candidate_promote",
    "conditional_opt_in",
    "demoted",
    "deprecated",
    "future",
    "git_or_manual",
    "internal_helper",
    "manual_trigger",
    "profile_scoped",
    "projected_elsewhere",
}


def _registered_claude_hook_paths() -> set[str]:
    data = json.loads((PROJECT_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks: set[str] = set()
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                hooks.update(f"hooks/{name}" for name in re.findall(r"/hooks/([A-Za-z0-9_-]+\.sh)", hook.get("command", "")))
    dispatcher = PROJECT_ROOT / "hooks" / "bash-hot-path-dispatcher.sh"
    if "hooks/bash-hot-path-dispatcher.sh" in hooks and dispatcher.exists():
        hooks.update(
            f"hooks/{name}"
            for name in re.findall(r"hooks/([A-Za-z0-9_-]+\.sh)", dispatcher.read_text(encoding="utf-8", errors="replace"))
        )
    return hooks


def _registered_codex_hook_paths() -> set[str]:
    data = json.loads((PROJECT_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    hooks: set[str] = set()
    for groups in data.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            for hook in group.get("hooks", []):
                hooks.update(f"hooks/{name}" for name in re.findall(r"hooks/([A-Za-z0-9_-]+\.sh)", hook.get("command", "")))
    return hooks


def _top_level_hook_paths() -> set[str]:
    return {f"hooks/{path.name}" for path in (PROJECT_ROOT / "hooks").glob("*.sh")}


def _manifest_entries() -> list[dict[str, str]]:
    payload = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    return payload.get("entries") or []


def test_unregistered_hooks_match_classification_manifest() -> None:
    unregistered = _top_level_hook_paths() - _registered_claude_hook_paths()
    entries = _manifest_entries()
    classified_unregistered = {
        entry.get("path")
        for entry in entries
        if entry.get("status") != "active"
    }
    assert unregistered == classified_unregistered, (
        "Every top-level hook absent from .claude/settings.json must be classified. "
        f"Missing: {sorted(unregistered - classified_unregistered)}; "
        f"stale: {sorted(classified_unregistered - unregistered)}"
    )

    registered = _registered_claude_hook_paths()
    stale_active = sorted(
        str(entry.get("path"))
        for entry in entries
        if entry.get("status") == "active" and entry.get("path") not in registered
    )
    assert not stale_active, f"active hook classification rows must be registered: {stale_active}"


def test_hook_registration_classifications_are_actionable() -> None:
    entries = _manifest_entries()
    assert entries, "classification manifest must not be empty"
    for entry in entries:
        assert entry.get("status") in VALID_STATUSES, entry
        assert entry.get("rationale"), entry
        assert entry.get("next_action"), entry
        assert (PROJECT_ROOT / str(entry.get("path", ""))).exists(), entry


def test_projected_elsewhere_hooks_are_actually_projected_elsewhere() -> None:
    codex_hooks = _registered_codex_hook_paths()
    offenders = [
        entry["path"]
        for entry in _manifest_entries()
        if entry.get("status") == "projected_elsewhere" and entry.get("path") not in codex_hooks
    ]
    assert not offenders, f"projected_elsewhere hooks missing from Codex projection: {offenders}"
