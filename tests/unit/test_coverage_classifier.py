"""Unit tests for scripts/cos-classify-coverage.py (ADR-041).

Tests: path heuristics, override via tags, tier count sanity.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import importlib.util

import pytest

# Load the module directly (filename has hyphens, not importable as package name)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
_MOD_PATH = _SCRIPTS_DIR / "cos-classify-coverage.py"

_spec = importlib.util.spec_from_file_location("cos_classify_coverage", _MOD_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

classify_component = _mod.classify_component
classify_all = _mod.classify_all
load_dormant_components = _mod.load_dormant_components
write_tiers_json = _mod.write_tiers_json


# ── Path heuristic tests ───────────────────────────────────────────────────────

@pytest.fixture()
def fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake project for testing."""
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    return tmp_path


def test_tier_a_destructive_hook(fake_project: Path):
    """hooks/destructive-rm-blocker.sh → Tier A."""
    tier = classify_component("hooks/destructive-rm-blocker.sh", fake_project)
    assert tier == "A", f"Expected Tier A, got {tier}"


def test_tier_a_secret_detector(fake_project: Path):
    """hooks/secret-detector.sh → Tier A."""
    tier = classify_component("hooks/secret-detector.sh", fake_project)
    assert tier == "A"


def test_tier_a_content_policy(fake_project: Path):
    """hooks/content-policy.sh → Tier A."""
    tier = classify_component("hooks/content-policy.sh", fake_project)
    assert tier == "A"


def test_tier_a_auto_rollback(fake_project: Path):
    """hooks/auto-rollback-trigger.sh → Tier A."""
    tier = classify_component("hooks/auto-rollback-trigger.sh", fake_project)
    assert tier == "A"


def test_tier_a_release_guard(fake_project: Path):
    """hooks/release-guard.sh → Tier A."""
    tier = classify_component("hooks/release-guard.sh", fake_project)
    assert tier == "A"


def test_tier_a_error_learning(fake_project: Path):
    """hooks/error-learning.sh → Tier A."""
    tier = classify_component("hooks/error-learning.sh", fake_project)
    assert tier == "A"


def test_tier_b_monitor(fake_project: Path):
    """hooks/agent-bus-monitor.sh → Tier B."""
    tier = classify_component("hooks/agent-bus-monitor.sh", fake_project)
    assert tier == "B"


def test_tier_b_heartbeat(fake_project: Path):
    """hooks/state-heartbeat.sh → Tier B."""
    tier = classify_component("hooks/state-heartbeat.sh", fake_project)
    assert tier == "B"


def test_tier_b_reaper(fake_project: Path):
    """hooks/session-end-reap.sh → Tier B."""
    tier = classify_component("hooks/session-end-reap.sh", fake_project)
    assert tier == "B"


def test_tier_c_mlflow(fake_project: Path):
    """hooks/mlflow-sync.sh → Tier C."""
    tier = classify_component("hooks/mlflow-sync.sh", fake_project)
    assert tier == "C"


def test_tier_c_valkey(fake_project: Path):
    """hooks/valkey-ensure.sh → Tier C."""
    tier = classify_component("hooks/valkey-ensure.sh", fake_project)
    assert tier == "C"


def test_tier_d_skill_md(fake_project: Path):
    """skills/auto-refine/SKILL.md → Tier D."""
    tier = classify_component("skills/auto-refine/SKILL.md", fake_project)
    assert tier == "D"


def test_tier_d_rules_md(fake_project: Path):
    """rules/token-economy.md → Tier D."""
    tier = classify_component("rules/token-economy.md", fake_project)
    assert tier == "D"


def test_tier_c_default_for_unknown(fake_project: Path):
    """Unrecognized component path → Tier C (default)."""
    tier = classify_component("scripts/some-random-utility.sh", fake_project)
    assert tier == "C"


# ── Override via TIER_OVERRIDE tag ─────────────────────────────────────────────

def test_tier_override_in_file(fake_project: Path):
    """File with TIER_OVERRIDE: A in first 20 lines → Tier A regardless of path."""
    override_file = fake_project / "hooks" / "mlflow-sync.sh"
    override_file.parent.mkdir(parents=True, exist_ok=True)
    override_file.write_text(
        "#!/usr/bin/env bash\n"
        "# TIER_OVERRIDE: A\n"
        "# This hook is actually safety-critical despite the mlflow name.\n"
        "exit 0\n"
    )
    tier = classify_component("hooks/mlflow-sync.sh", fake_project)
    assert tier == "A", f"TIER_OVERRIDE: A must force Tier A, got {tier}"


def test_tier_override_case_insensitive(fake_project: Path):
    """TIER_OVERRIDE is case-insensitive (tier_override: b → Tier B)."""
    test_file = fake_project / "scripts" / "unknown-tool.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# tier_override: B\nprint('hello')\n")
    tier = classify_component("scripts/unknown-tool.py", fake_project)
    assert tier == "B", f"tier_override: B (lowercase) must force Tier B, got {tier}"


def test_tier_override_only_first_20_lines(fake_project: Path):
    """TIER_OVERRIDE after line 20 must be ignored."""
    test_file = fake_project / "hooks" / "regular-hook.sh"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# line {}\n".format(i) for i in range(25)]
    lines.append("# TIER_OVERRIDE: A\n")  # line 26, after the 20-line window
    test_file.write_text("".join(lines))
    # Path has no Tier A keywords → should be Tier C (default)
    tier = classify_component("hooks/regular-hook.sh", fake_project)
    assert tier == "C", f"Override after line 20 must be ignored, got {tier}"


# ── Tier count sanity ──────────────────────────────────────────────────────────

def _write_audit_jsonl(audit_path: Path, components: list[tuple[str, str]]) -> None:
    """Write fake aspirational-audit.jsonl with given (component, classification) pairs."""
    with audit_path.open("w") as fh:
        for component, classification in components:
            row = {
                "source": "aspirational-audit",
                "event_type": "component.classified",
                "schema_version": "1.0",
                "timestamp": "2026-04-20T00:00:00+00:00",
                "payload": {
                    "component": component,
                    "classification": classification,
                    "signals": {},
                    "reason": "test",
                },
            }
            fh.write(json.dumps(row) + "\n")


def test_load_dormant_skips_real_and_metadata(fake_project: Path):
    """load_dormant_components must exclude REAL and METADATA classifications."""
    audit_file = fake_project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
    _write_audit_jsonl(audit_file, [
        ("hooks/real-hook.sh", "REAL"),
        ("hooks/meta-helper.sh", "METADATA"),
        ("hooks/dormant-hook.sh", "DORMANT"),
        ("hooks/aspirational-hook.sh", "ASPIRATIONAL"),
    ])
    components = load_dormant_components(audit_file)
    assert "hooks/dormant-hook.sh" in components
    assert "hooks/aspirational-hook.sh" in components
    assert "hooks/real-hook.sh" not in components
    assert "hooks/meta-helper.sh" not in components


def test_classify_all_tier_distribution(fake_project: Path):
    """classify_all must return correct tier distribution for known components."""
    audit_file = fake_project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
    _write_audit_jsonl(audit_file, [
        ("hooks/secret-detector.sh", "DORMANT"),        # Tier A
        ("hooks/release-guard.sh", "DORMANT"),           # Tier A
        ("hooks/agent-bus-monitor.sh", "DORMANT"),       # Tier B
        ("hooks/mlflow-sync.sh", "DORMANT"),             # Tier C
        ("hooks/valkey-ensure.sh", "ASPIRATIONAL"),      # Tier C
        ("skills/auto-refine/SKILL.md", "DORMANT"),      # Tier D
    ])
    tiers = classify_all(fake_project, audit_file)
    assert len(tiers) == 6
    tier_a = [c for c, t in tiers.items() if t == "A"]
    tier_b = [c for c, t in tiers.items() if t == "B"]
    tier_c = [c for c, t in tiers.items() if t == "C"]
    tier_d = [c for c, t in tiers.items() if t == "D"]
    assert len(tier_a) == 2, f"Expected 2 Tier A, got {tier_a}"
    assert len(tier_b) == 1, f"Expected 1 Tier B, got {tier_b}"
    assert len(tier_c) == 2, f"Expected 2 Tier C, got {tier_c}"
    assert len(tier_d) == 1, f"Expected 1 Tier D, got {tier_d}"


def test_write_tiers_json_roundtrip(fake_project: Path, tmp_path: Path):
    """write_tiers_json must produce valid JSON that reads back correctly."""
    tiers = {
        "hooks/secret-detector.sh": "A",
        "hooks/mlflow-sync.sh": "C",
        "skills/foo/SKILL.md": "D",
    }
    output = tmp_path / "tiers.json"
    write_tiers_json(tiers, output)
    assert output.exists()
    loaded = json.loads(output.read_text())
    assert loaded == dict(sorted(tiers.items()))


def test_classify_all_deduplicates_components(fake_project: Path):
    """If a component appears multiple times in audit, it must be classified once."""
    audit_file = fake_project / ".cognitive-os" / "metrics" / "aspirational-audit.jsonl"
    _write_audit_jsonl(audit_file, [
        ("hooks/secret-detector.sh", "DORMANT"),
        ("hooks/secret-detector.sh", "DORMANT"),  # duplicate
        ("hooks/secret-detector.sh", "ASPIRATIONAL"),  # duplicate with different classification
    ])
    tiers = classify_all(fake_project, audit_file)
    # Should appear exactly once
    keys = list(tiers.keys())
    assert keys.count("hooks/secret-detector.sh") == 1
