"""Tests for Hook Architecture — sync generator to 7 event types.

Validates that:
- set-security-profile.sh has valid bash syntax
- All profiles (minimal, standard, paranoid) are defined
- paranoid ⊇ standard ⊇ minimal (superset property)
- Core safety hooks are present in minimal
- Quality hooks are present in standard
- hooks/_lib/timing.sh exists and has valid bash syntax
- Every registered hook has a corresponding .sh file in hooks/
"""

import json
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR_SCRIPT = PROJECT_ROOT / "scripts" / "set-security-profile.sh"
HOOKS_DIR = PROJECT_ROOT / "hooks"
TIMING_LIB = PROJECT_ROOT / "hooks" / "_lib" / "timing.sh"
SETTINGS_FILE = PROJECT_ROOT / ".claude" / "settings.json"


def _generate_profile(profile: str) -> dict:
    """Run set-security-profile.sh for a profile and return parsed JSON."""
    original_exists = SETTINGS_FILE.exists()
    original_text = SETTINGS_FILE.read_text() if original_exists else None
    try:
        result = subprocess.run(
            ["bash", str(GENERATOR_SCRIPT), profile],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Generator failed for {profile}: {result.stderr}"
        assert SETTINGS_FILE.exists(), "settings.json was not created"
        return json.loads(SETTINGS_FILE.read_text())
    finally:
        if original_exists and original_text is not None:
            SETTINGS_FILE.write_text(original_text)
        elif SETTINGS_FILE.exists():
            SETTINGS_FILE.unlink()


def _extract_hooks(settings: dict) -> set:
    """Extract all hook filenames from a settings dict."""
    hooks = set()
    for event_type, groups in settings.get("hooks", {}).items():
        for group in groups:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                # Extract hook filename from command like: bash "$CLAUDE_PROJECT_DIR/hooks/foo.sh"
                m = re.search(r"hooks/([^\s\"]+\.sh)", cmd)
                if m:
                    hooks.add(m.group(1))
    return hooks


def _get_all_profiles():
    """Generate settings for all three profiles and return (minimal, standard, paranoid) hook sets."""
    profiles = {}
    for profile in ("minimal", "standard", "paranoid"):
        data = _generate_profile(profile)
        profiles[profile] = _extract_hooks(data)
    return profiles


# ── Test 1: Generator bash syntax is valid ──────────────────────────────────

def test_generator_syntax_valid():
    """bash -n on set-security-profile.sh must exit 0."""
    result = subprocess.run(
        ["bash", "-n", str(GENERATOR_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Syntax error in set-security-profile.sh:\n{result.stderr}"
    )


# ── Test 2: All three profiles are defined ───────────────────────────────────

def test_all_profiles_defined():
    """Calling the generator with each profile name must succeed."""
    for profile in ("minimal", "standard", "paranoid"):
        data = _generate_profile(profile)
        assert "hooks" in data, f"No 'hooks' key in settings.json for {profile}"


# ── Test 3: paranoid ⊇ standard (superset) ──────────────────────────────────

def test_paranoid_superset_standard():
    """Every hook in standard must also be in paranoid."""
    profiles = _get_all_profiles()
    standard = profiles["standard"]
    paranoid = profiles["paranoid"]
    missing = standard - paranoid
    assert not missing, (
        f"Hooks in standard but NOT in paranoid (violates paranoid ⊇ standard):\n"
        + "\n".join(f"  {h}" for h in sorted(missing))
    )


# ── Test 4: standard ⊇ minimal (superset) ───────────────────────────────────

def test_standard_superset_minimal():
    """Every hook in minimal must also be in standard."""
    profiles = _get_all_profiles()
    minimal = profiles["minimal"]
    standard = profiles["standard"]
    missing = minimal - standard
    assert not missing, (
        f"Hooks in minimal but NOT in standard (violates standard ⊇ minimal):\n"
        + "\n".join(f"  {h}" for h in sorted(missing))
    )


# ── Test 5: minimal has core safety hooks ────────────────────────────────────

def test_minimal_has_core_safety():
    """Minimal profile must include fundamental safety hooks."""
    data = _generate_profile("minimal")
    hooks = _extract_hooks(data)
    required = {
        "secret-detector.sh",
        "rate-limiter.sh",
        "error-pipeline.sh",
        "session-init.sh",
        "session-cleanup.sh",
    }
    missing = required - hooks
    assert not missing, (
        f"Core safety hooks missing from minimal profile:\n"
        + "\n".join(f"  {h}" for h in sorted(missing))
    )


# ── Test 6: standard has quality hooks ───────────────────────────────────────

def test_standard_has_quality_hooks():
    """Standard profile must include quality and governance hooks."""
    data = _generate_profile("standard")
    hooks = _extract_hooks(data)
    required = {
        "dispatch-gate.sh",
        "clarification-gate.sh",
        "state-heartbeat.sh",
        "completion-gate.sh",
        "content-policy.sh",
    }
    missing = required - hooks
    assert not missing, (
        f"Quality hooks missing from standard profile:\n"
        + "\n".join(f"  {h}" for h in sorted(missing))
    )


# ── Test 7: timing.sh exists and has valid bash syntax ───────────────────────

def test_timing_lib_exists():
    """hooks/_lib/timing.sh must exist and pass bash -n syntax check."""
    assert TIMING_LIB.exists(), f"hooks/_lib/timing.sh does not exist at {TIMING_LIB}"
    result = subprocess.run(
        ["bash", "-n", str(TIMING_LIB)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Syntax error in hooks/_lib/timing.sh:\n{result.stderr}"
    )


# ── Test 8: all registered hooks exist as files ──────────────────────────────

def test_registered_hooks_exist_as_files():
    """Every hook registered in any profile must have a corresponding .sh file."""
    all_hooks: set = set()
    for profile in ("minimal", "standard", "paranoid"):
        data = _generate_profile(profile)
        all_hooks |= _extract_hooks(data)

    missing_files = []
    for hook_name in sorted(all_hooks):
        hook_path = HOOKS_DIR / hook_name
        if not hook_path.exists():
            missing_files.append(hook_name)

    assert not missing_files, (
        f"Registered hooks without .sh files in hooks/:\n"
        + "\n".join(f"  {h}" for h in missing_files)
    )


# ── Test 9: hook counts are in expected range ────────────────────────────────

def test_hook_counts_in_range():
    """Minimal, standard, paranoid should have increasing hook counts."""
    counts = {}
    for profile in ("minimal", "standard", "paranoid"):
        data = _generate_profile(profile)
        counts[profile] = len(_extract_hooks(data))

    assert counts["minimal"] > 0, "Minimal profile has no hooks"
    assert counts["standard"] > counts["minimal"], (
        f"Standard ({counts['standard']}) must have more hooks than minimal ({counts['minimal']})"
    )
    assert counts["paranoid"] > counts["standard"], (
        f"Paranoid ({counts['paranoid']}) must have more hooks than standard ({counts['standard']})"
    )
    # Approximate range checks (loose, to allow growth)
    assert counts["minimal"] >= 10, f"Minimal too small: {counts['minimal']}"
    assert counts["standard"] >= 20, f"Standard too small: {counts['standard']}"
    assert counts["paranoid"] >= 40, f"Paranoid too small: {counts['paranoid']}"
