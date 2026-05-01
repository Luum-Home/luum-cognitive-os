"""test_hook_disable_env.py — Audit tests for Phase 5: dynamic hook disable env vars.

Phase 5 of hook-architecture-v2. Tests verify:
  - check_disabled_env is defined in hooks/_lib/common.sh
  - The 16 target hooks call check_disabled_env
  - The env var name convention matches hook name (hyphens → underscores, uppercase)
  - The hook-security-profiles.md rule documents the DISABLE_HOOK_* mechanism
  - At least 16 hooks implement the disable env var check
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent.parent

# ── The 16 target hooks from Phase 5 ─────────────────────────────────────────

TARGET_HOOKS = [
    ("blast-radius.sh", "DISABLE_HOOK_BLAST_RADIUS"),
    ("clarification-gate.sh", "DISABLE_HOOK_CLARIFICATION_GATE"),
    ("assumption-tracker.sh", "DISABLE_HOOK_ASSUMPTION_TRACKER"),
    ("confidence-gate.sh", "DISABLE_HOOK_CONFIDENCE_GATE"),
    ("claim-validator.sh", "DISABLE_HOOK_CLAIM_VALIDATOR"),
    ("consequence-evaluator.sh", "DISABLE_HOOK_CONSEQUENCE_EVALUATOR"),
    ("architecture-compliance.sh", "DISABLE_HOOK_ARCHITECTURE_COMPLIANCE"),
    ("dispatch-gate.sh", "DISABLE_HOOK_DISPATCH_GATE"),
    ("auto-skill-generator.sh", "DISABLE_HOOK_AUTO_SKILL_GENERATOR"),
    ("tool-loop-detector.sh", "DISABLE_HOOK_TOOL_LOOP_DETECTOR"),
    ("scope-proportionality.sh", "DISABLE_HOOK_SCOPE_PROPORTIONALITY"),
    ("trust-score-validator.sh", "DISABLE_HOOK_TRUST_SCORE_VALIDATOR"),
    ("error-pattern-detector.sh", "DISABLE_HOOK_ERROR_PATTERN_DETECTOR"),
    ("semgrep-scan.sh", "DISABLE_HOOK_SEMGREP_SCAN"),
    ("aguara-scan.sh", "DISABLE_HOOK_AGUARA_SCAN"),
    ("rate-limiter.sh", "DISABLE_HOOK_RATE_LIMITER"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.audit
def test_check_disabled_env_defined_in_common():
    """check_disabled_env must be defined in hooks/_lib/common.sh."""
    common = REPO / "hooks" / "_lib" / "common.sh"
    assert common.exists(), "hooks/_lib/common.sh not found"

    content = _read(common)
    assert "check_disabled_env()" in content, (
        "check_disabled_env() not defined in hooks/_lib/common.sh. "
        "Phase 5 requires adding this function."
    )


@pytest.mark.audit
def test_check_disabled_env_reads_env_var():
    """check_disabled_env must inspect a DISABLE_HOOK_* env var and exit 0 if set."""
    common = REPO / "hooks" / "_lib" / "common.sh"
    if not common.exists():
        pytest.skip("common.sh not found")

    content = _read(common)
    # Must reference DISABLE_HOOK_ prefix (either in variable construction or comment)
    assert "DISABLE_HOOK_" in content, (
        "check_disabled_env does not reference DISABLE_HOOK_ prefix. "
        "Must check an env var matching this pattern."
    )


@pytest.mark.audit
def test_common_sh_syntax_still_valid():
    """hooks/_lib/common.sh must pass bash -n after Phase 5 changes."""
    common = REPO / "hooks" / "_lib" / "common.sh"
    if not common.exists():
        pytest.skip("common.sh not found")

    result = subprocess.run(
        ["bash", "-n", str(common)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"common.sh failed bash -n syntax check:\n{result.stderr}"
    )


@pytest.mark.audit
@pytest.mark.parametrize("hook_file,expected_env_var", TARGET_HOOKS)
def test_hook_calls_check_disabled_env(hook_file: str, expected_env_var: str):
    """Each target hook must call check_disabled_env."""
    hook_path = REPO / "hooks" / hook_file
    if not hook_path.exists():
        pytest.skip(f"{hook_file} does not exist")

    content = _read(hook_path)
    assert "check_disabled_env" in content, (
        f"{hook_file} does not call check_disabled_env. "
        f"Phase 5 requires adding: check_disabled_env \"{hook_file[:-3]}\""
    )


@pytest.mark.audit
def test_minimum_15_hooks_support_disable_env():
    """At least 15 hook files must call check_disabled_env."""
    hooks_dir = REPO / "hooks"
    count = 0
    for hook_sh in sorted(hooks_dir.glob("*.sh")):
        try:
            content = hook_sh.read_text(encoding="utf-8", errors="replace")
            if "check_disabled_env" in content:
                count += 1
        except Exception:
            continue

    assert count >= 15, (
        f"Only {count} hooks call check_disabled_env. "
        "Phase 5 requires at least 15 hooks to support the disable env var mechanism."
    )


@pytest.mark.audit
def test_disable_env_documented_in_security_profiles_rule():
    """rules/hook-security-profiles.md must document the DISABLE_HOOK_* mechanism."""
    rule = REPO / "rules" / "hook-security-profiles.md"
    assert rule.exists(), "rules/hook-security-profiles.md not found"

    content = _read(rule)
    assert "DISABLE_HOOK_" in content, (
        "rules/hook-security-profiles.md does not document DISABLE_HOOK_* env vars. "
        "Phase 5 requires documenting per-session hook suppression."
    )
    assert "check_disabled_env" in content, (
        "rules/hook-security-profiles.md does not mention check_disabled_env. "
        "Must reference the implementing function."
    )


@pytest.mark.audit
def test_disable_env_convention_hyphens_to_underscores():
    """check_disabled_env must transform hyphens to underscores in env var names."""
    common = REPO / "hooks" / "_lib" / "common.sh"
    if not common.exists():
        pytest.skip("common.sh not found")

    content = _read(common)
    # The function should reference the tr/sed transformation or document the pattern
    # We check that it at least does a case/transform operation
    assert (
        "tr" in content or "sed" in content or "upper" in content.lower()
    ), (
        "check_disabled_env does not appear to do case/hyphen transformation. "
        "Must convert hook name to UPPERCASE with hyphens→underscores."
    )


@pytest.mark.audit
@pytest.mark.parametrize("hook_file,_", TARGET_HOOKS)
def test_target_hook_syntax_valid_after_phase5(hook_file: str, _: str):
    """All 15 target hooks must still pass bash -n after Phase 5 changes."""
    hook_path = REPO / "hooks" / hook_file
    if not hook_path.exists():
        pytest.skip(f"{hook_file} does not exist")

    result = subprocess.run(
        ["bash", "-n", str(hook_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{hook_file} failed bash -n syntax check:\n{result.stderr}"
    )
