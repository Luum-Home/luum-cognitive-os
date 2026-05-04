"""Contracts for hook-enforced rule exclusions.

Rules listed in hooks/self-install.sh:EXCLUDED_RULES are omitted from startup
context to reduce token load. That optimization is only safe when the referenced
hook is actually projected into the active harness settings. These tests prevent
"excluded from context" from silently becoming "not enforced anywhere".
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.audit]

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SELF_INSTALL = PROJECT_ROOT / "hooks" / "self-install.sh"
HOOKS_DIR = PROJECT_ROOT / "hooks"
SETTINGS_PATH = PROJECT_ROOT / ".claude" / "settings.json"
CONFIG_PATH = PROJECT_ROOT / "cognitive-os.yaml"


def _excluded_rule_hook_claims() -> dict[str, set[str]]:
    """Return EXCLUDED_RULES entries that claim hook enforcement via `# → ...`."""
    text = SELF_INSTALL.read_text(encoding="utf-8")
    claims: dict[str, set[str]] = {}
    in_array = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("EXCLUDED_RULES=("):
            in_array = True
            continue
        if in_array and line == ")":
            break
        if not in_array or not line.startswith('"'):
            continue
        rule_match = re.match(r'"([^"]+\.md)"\s*(?:#\s*(.*))?$', line)
        if not rule_match:
            continue
        rule_name, comment = rule_match.groups()
        comment = comment or ""
        if "agent-instruction-only" in comment or "no hook" in comment:
            continue
        scripts = set(re.findall(r"([A-Za-z0-9_-]+\.sh)", comment))
        if scripts:
            claims[rule_name] = scripts
    return claims


def _settings_hook_names() -> set[str]:
    data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for groups in data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                names.update(re.findall(r"/hooks/([A-Za-z0-9_-]+\.sh)", hook.get("command", "")))
    return names


def _canonical_hook_scripts() -> set[str]:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    hooks = (config.get("harness") or {}).get("hooks") or {}
    return {
        str(entry.get("script", "")).removeprefix("hooks/")
        for entry in hooks.values()
        if isinstance(entry, dict) and str(entry.get("script", "")).startswith("hooks/")
    }


def test_excluded_hook_enforced_rules_reference_existing_hooks() -> None:
    claims = _excluded_rule_hook_claims()
    assert claims, "No hook-enforced EXCLUDED_RULES claims parsed from self-install.sh"
    missing = {
        rule: sorted(script for script in scripts if not (HOOKS_DIR / script).exists())
        for rule, scripts in claims.items()
    }
    missing = {rule: scripts for rule, scripts in missing.items() if scripts}
    assert not missing, (
        "EXCLUDED_RULES claims hook enforcement through missing hook files: "
        f"{missing}. Either create the hook, point at the renamed hook, or mark "
        "the rule agent-instruction-only."
    )


def test_excluded_hook_enforced_rules_are_in_canonical_registry() -> None:
    claims = _excluded_rule_hook_claims()
    canonical = _canonical_hook_scripts()
    missing = {
        rule: sorted(scripts - canonical)
        for rule, scripts in claims.items()
        # pre-commit-gate is a Git hook path managed outside harness.hooks.
        if rule != "pre-commit-gate.md" and scripts - canonical
    }
    assert not missing, (
        "EXCLUDED_RULES removed rule context but the enforcement hook is absent "
        f"from cognitive-os.yaml > harness.hooks: {missing}. Add it to the "
        "canonical registry before excluding the rule."
    )


def test_excluded_hook_enforced_rules_are_projected_to_claude_settings() -> None:
    claims = _excluded_rule_hook_claims()
    registered = _settings_hook_names()
    missing = {
        rule: sorted(scripts - registered)
        for rule, scripts in claims.items()
        # Git hooks are enforced outside Claude Code settings.
        if rule != "pre-commit-gate.md" and scripts - registered
    }
    assert not missing, (
        "EXCLUDED_RULES removed rule context but the enforcement hook is absent "
        f"from .claude/settings.json: {missing}. Run apply-efficiency-profile.sh "
        "after updating the canonical registry/driver."
    )
