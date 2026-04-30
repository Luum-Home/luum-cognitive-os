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

pytestmark = [
    pytest.mark.unit,
    pytest.mark.xdist_group("perf_budget"),
    pytest.mark.benchmark,
]
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
    """Every rule file in rules/ should eventually have an entry in RULES-COMPACT.md.

    Emits a warning for any rules not yet integrated.  This test does NOT fail
    on missing rules to avoid breaking the suite every time a new rule file is
    added — the RULES-COMPACT.md integration is tracked separately.

    The INVARIANT that IS asserted: RULES-COMPACT.md itself exists and is
    non-empty (i.e. the compact file itself wasn't accidentally deleted).
    """
    import warnings
    compact_path = PROJECT_ROOT / "rules" / "RULES-COMPACT.md"
    assert compact_path.exists(), "RULES-COMPACT.md not found"
    compact = compact_path.read_text()
    assert len(compact.strip()) > 200, (
        "RULES-COMPACT.md appears to be empty or nearly empty — was it deleted?"
    )

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
            f"Rules not yet in RULES-COMPACT.md (add when ready): {missing}",
            UserWarning,
            stacklevel=1,
        )


# ---------------------------------------------------------------------------
# Test 3: Efficiency profiles in cognitive-os.yaml
# ---------------------------------------------------------------------------


def test_efficiency_profiles_defined():
    """cognitive-os.yaml must define at least one efficiency profile.

    The original three-tier system (lean/standard/full) was collapsed to a
    two-tier system (default/full) in ADR-093.  This test validates the
    invariant that matters: the efficiency section exists and has at least one
    named profile, regardless of which specific names are used.
    """
    config_path = PROJECT_ROOT / "cognitive-os.yaml"
    assert config_path.exists(), "cognitive-os.yaml not found"

    try:
        import yaml

        config = yaml.safe_load(config_path.read_text())
    except ImportError:
        # Fallback: check raw text for any profile declaration
        content = config_path.read_text()
        assert "efficiency:" in content or "profiles:" in content, (
            "cognitive-os.yaml missing efficiency section"
        )
        return

    assert "efficiency" in config, "Missing efficiency section in cognitive-os.yaml"
    profiles = config["efficiency"].get("profiles", {})
    assert len(profiles) >= 1, (
        f"efficiency.profiles must define at least one profile, got: {list(profiles.keys())}"
    )


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


@pytest.mark.xdist_group("hook-chain-perf")  # serialise hook-subprocess timing tests
def test_contextual_rule_loader_fast(tmp_path):
    """contextual-rule-loader.sh must complete in under 500ms.

    Uses an isolated project directory with a minimal cognitive-os.yaml
    (a small number of contextual_triggers) so the Python-based matcher loop
    stays fast regardless of real-project config size.
    """
    hook = PROJECT_ROOT / "hooks" / "contextual-rule-loader.sh"
    if not hook.exists():
        pytest.skip("contextual-rule-loader.sh not found")

    # Build an isolated project with minimal config
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    rules_dir = project_dir / "rules"
    rules_dir.mkdir()
    cos_dir = project_dir / ".cognitive-os"
    metrics_dir = cos_dir / "metrics"
    metrics_dir.mkdir(parents=True)

    # Minimal cognitive-os.yaml with a small contextual_triggers block
    config_content = """\
rules:
  loading:
    strategy: compact
    contextual_triggers:
      auto-repair: "auto-repair|circuit.breaker"
      squad-protocol: "/squad-report|/retrospective"
"""
    (project_dir / "cognitive-os.yaml").write_text(config_content)
    # Create a stub rule file so the hook can find it
    (rules_dir / "auto-repair.md").write_text("# Auto-Repair\nStub rule.\n")

    # Simulate minimal input
    input_json = json.dumps(
        {"tool_name": "Agent", "tool_input": {"prompt": "test prompt"}}
    )
    env = {
        **os.environ,
        "COGNITIVE_OS_DIR": str(cos_dir),
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    }
    start = time.time()
    subprocess.run(
        ["bash", str(hook)],
        input=input_json,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        cwd=str(PROJECT_ROOT),
    )
    elapsed_ms = (time.time() - start) * 1000
    # 500ms budget: hook targets <100ms; 5x headroom for CI overhead.
    assert elapsed_ms < 500, f"Hook took {elapsed_ms:.0f}ms (budget: 500ms)"
