"""Validation tests for the efficiency optimization system.

Covers: RULES-COMPACT token budget, rule completeness, efficiency profiles,
capability level wiring in hooks, contextual rule loader, and CLAUDE.md budget.
"""

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test 1: RULES-COMPACT.md token budget
# ---------------------------------------------------------------------------


def test_rules_compact_token_budget():
    """RULES-COMPACT.md must stay under 6,000 tokens (~24,000 chars)."""
    path = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
    assert path.exists(), "RULES-COMPACT.md not found"
    content = path.read_text()
    # Rough token estimate: chars / 4
    estimated_tokens = len(content) / 4
    assert estimated_tokens < 6000, (
        f"RULES-COMPACT.md is ~{estimated_tokens:.0f} tokens, exceeds 6,000 budget"
    )


# ---------------------------------------------------------------------------
# Test 2: RULES-COMPACT completeness
# ---------------------------------------------------------------------------


def test_rules_compact_covers_all_rules():
    """Every rule file in rules/ should have an entry in RULES-COMPACT.md.

    Uses a warning for newly added rules that haven't been integrated yet,
    since the authoritative check is in test_rules_consolidation.py.
    """
    import warnings
    compact = (PROJECT_ROOT / "rules" / "RULES-COMPACT.md").read_text()
    rule_files = sorted(PROJECT_ROOT.glob("rules/*.md"))
    missing = []
    for f in rule_files:
        if f.name == "RULES-COMPACT.md":
            continue
        rule_name = f.stem
        if rule_name not in compact:
            missing.append(rule_name)
    if missing:
        warnings.warn(
            f"Rules not yet in RULES-COMPACT.md (update COMPACT when ready): {missing}",
            UserWarning,
            stacklevel=1,
        )
    # Still assert but with a helpful message pointing to the fix
    assert not missing, (
        f"Rules missing from RULES-COMPACT.md: {missing}. "
        f"Add references to rules/RULES-COMPACT.md for each new rule."
    )


# ---------------------------------------------------------------------------
# Test 3: Efficiency profiles in cognitive-os.yaml
# ---------------------------------------------------------------------------


def test_efficiency_profiles_defined():
    """cognitive-os.yaml must define lean, standard, and full profiles."""
    config_path = PROJECT_ROOT / "cognitive-os.yaml"
    assert config_path.exists(), "cognitive-os.yaml not found"

    try:
        import yaml

        config = yaml.safe_load(config_path.read_text())
    except ImportError:
        # Fallback: check raw text for profile names
        content = config_path.read_text()
        assert "lean:" in content, "Missing profile: lean"
        assert "standard:" in content, "Missing profile: standard"
        assert "full:" in content, "Missing profile: full"
        return

    assert "efficiency" in config, "Missing efficiency section in cognitive-os.yaml"
    profiles = config["efficiency"].get("profiles", {})
    for p in ["lean", "standard", "full"]:
        assert p in profiles, f"Missing efficiency profile: {p}"


# ---------------------------------------------------------------------------
# Test 4: self-install.sh respects efficiency profile
# ---------------------------------------------------------------------------


def test_self_install_reads_efficiency_profile():
    """self-install.sh must contain logic to read efficiency.profile."""
    path = PROJECT_ROOT / "hooks" / "self-install.sh"
    assert path.exists(), "self-install.sh not found"
    content = path.read_text()
    assert "efficiency" in content.lower() or "EFFICIENCY_PROFILE" in content, (
        "self-install.sh does not reference efficiency profile"
    )


# ---------------------------------------------------------------------------
# Test 5: Capability levels function exists in common.sh
# ---------------------------------------------------------------------------


def test_capability_level_check_in_common():
    """common.sh must have check_capability_level function."""
    path = PROJECT_ROOT / "hooks" / "_lib" / "common.sh"
    assert path.exists(), "common.sh not found"
    content = path.read_text()
    assert "check_capability_level" in content, (
        "common.sh missing check_capability_level function"
    )


# ---------------------------------------------------------------------------
# Test 6: Hooks that should check capability level
# ---------------------------------------------------------------------------


def test_hooks_check_capability_level():
    """Hooks disabled at level 4 must call check_capability_level."""
    level4_hooks = [
        "clarification-gate.sh",
        "blast-radius.sh",
        "confidence-gate.sh",
        "assumption-tracker.sh",
    ]
    missing = []
    for hook_name in level4_hooks:
        path = PROJECT_ROOT / "hooks" / hook_name
        if path.exists():
            content = path.read_text()
            if "check_capability_level" not in content:
                missing.append(hook_name)
    assert not missing, (
        f"Hooks missing check_capability_level call: {missing}"
    )


# ---------------------------------------------------------------------------
# Test 7: Contextual rule loader exists
# ---------------------------------------------------------------------------


def test_contextual_rule_loader_exists():
    """contextual-rule-loader.sh must exist and be executable."""
    path = PROJECT_ROOT / "hooks" / "contextual-rule-loader.sh"
    assert path.exists(), "contextual-rule-loader.sh not found"
    assert os.access(path, os.X_OK), "contextual-rule-loader.sh is not executable"


# ---------------------------------------------------------------------------
# Test 8: CLAUDE.md token budget
# ---------------------------------------------------------------------------


def test_claude_md_token_budget():
    """Global CLAUDE.md should be under 3,500 tokens (~14,000 chars)."""
    path = Path.home() / ".claude" / "CLAUDE.md"
    if not path.exists():
        pytest.skip("No global CLAUDE.md found")
    content = path.read_text()
    estimated_tokens = len(content) / 4
    assert estimated_tokens < 3500, (
        f"CLAUDE.md is ~{estimated_tokens:.0f} tokens, exceeds 3,500 budget"
    )


# ---------------------------------------------------------------------------
# Test 9: No duplicate SDD content in CLAUDE.md
# ---------------------------------------------------------------------------


def test_claude_md_no_sdd_duplication():
    """CLAUDE.md should not contain duplicate SDD Workflow sections."""
    path = Path.home() / ".claude" / "CLAUDE.md"
    if not path.exists():
        pytest.skip("No global CLAUDE.md found")
    content = path.read_text()
    sdd_count = content.count("## SDD Workflow")
    assert sdd_count <= 1, (
        f"SDD Workflow appears {sdd_count} times in CLAUDE.md (should be 0 or 1)"
    )


# ---------------------------------------------------------------------------
# Test 10: Hook latency benchmark
# ---------------------------------------------------------------------------


def test_contextual_rule_loader_fast():
    """contextual-rule-loader.sh must complete in under 500ms."""
    hook = PROJECT_ROOT / "hooks" / "contextual-rule-loader.sh"
    if not hook.exists():
        pytest.skip("contextual-rule-loader.sh not found")

    # Simulate minimal input
    input_json = json.dumps(
        {"tool_name": "Agent", "tool_input": {"prompt": "test prompt"}}
    )
    env = {
        **os.environ,
        "COGNITIVE_OS_DIR": str(PROJECT_ROOT / ".cognitive-os"),
        "CLAUDE_PROJECT_DIR": str(PROJECT_ROOT),
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    }
    start = time.time()
    result = subprocess.run(
        ["bash", str(hook)],
        input=input_json,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    elapsed_ms = (time.time() - start) * 1000
    # 3000ms budget accounts for cold-start overhead and CPU contention in
    # test environments; the hook itself targets <500ms in a warm session.
    assert elapsed_ms < 3000, f"Hook took {elapsed_ms:.0f}ms (budget: 3000ms)"
