"""Tests for scripts/measure_expansion.py.

Uses synthetic rule files across 3 tiers so results are deterministic and
independent of the real rules/ directory content.
"""
from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root on path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from measure_expansion import measure_buffer  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _write_rule(rules_dir: Path, name: str, tier: int, content: str) -> Path:
    """Write a synthetic rule file with a TIER frontmatter comment."""
    path = rules_dir / f"{name}.md"
    path.write_text(f"<!-- TIER: {tier} -->\n# {name}\n\n{content}\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMeasureBuffer:
    """Verify measure_buffer() counts bytes/tokens/unexpanded correctly."""

    def test_full_expansion_expands_all_tiers(self, tmp_path, monkeypatch):
        """tier_filter=None should expand all 3 rules and leave 0 unexpanded."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "Tier-0 content.")
        _write_rule(rules_dir, "rule-tier1", 1, "Tier-1 content.")
        _write_rule(rules_dir, "rule-tier2", 2, "Tier-2 content.")

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
        # Invalidate module-level cached _rules_dir by forcing re-import path.
        # ref_key_loader uses _project_root() which reads env at call time — OK.

        text = "Before [`rule-tier0`] middle [`rule-tier1`] and [`rule-tier2`] after."
        results = measure_buffer(text)

        full = results["full (None)"]
        assert full["unexpanded_keys"] == 0, (
            f"Expected 0 unexpanded in full mode, got {full['unexpanded_keys']}"
        )

    def test_tier01_leaves_tier2_unexpanded(self, tmp_path, monkeypatch):
        """tier_filter={0,1} should expand Tier-0 and Tier-1, leave Tier-2 intact."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "Tier-0 content.")
        _write_rule(rules_dir, "rule-tier1", 1, "Tier-1 content.")
        _write_rule(rules_dir, "rule-tier2", 2, "Tier-2 content.")

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "A [`rule-tier0`] B [`rule-tier1`] C [`rule-tier2`] D."
        results = measure_buffer(text)

        r = results["{0,1}"]
        assert r["unexpanded_keys"] == 1, (
            f"Expected exactly 1 unexpanded key (Tier-2) in {{0,1}} mode, got {r['unexpanded_keys']}"
        )

    def test_tier0_only_leaves_tier1_and_tier2_unexpanded(self, tmp_path, monkeypatch):
        """tier_filter={0} should only expand Tier-0; Tier-1 and Tier-2 remain."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "Tier-0 content.")
        _write_rule(rules_dir, "rule-tier1", 1, "Tier-1 content.")
        _write_rule(rules_dir, "rule-tier2", 2, "Tier-2 content.")

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "A [`rule-tier0`] B [`rule-tier1`] C [`rule-tier2`] D."
        results = measure_buffer(text)

        r = results["{0}"]
        assert r["unexpanded_keys"] == 2, (
            f"Expected 2 unexpanded keys (Tier-1 + Tier-2) in {{0}} mode, got {r['unexpanded_keys']}"
        )

    def test_token_estimate_is_bytes_over_four(self, tmp_path, monkeypatch):
        """tokens_est should equal round(bytes / 4) for every config."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "x" * 100)

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "Hello [`rule-tier0`] world."
        results = measure_buffer(text)

        for label, stats in results.items():
            expected_tokens = round(stats["bytes"] / 4)
            assert stats["tokens_est"] == expected_tokens, (
                f"{label}: tokens_est={stats['tokens_est']} != round({stats['bytes']}/4)={expected_tokens}"
            )

    def test_bytes_monotonically_increase_with_tiers(self, tmp_path, monkeypatch):
        """More tiers allowed → more content → more bytes (or equal if all same tier)."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "Tier0 " * 50)
        _write_rule(rules_dir, "rule-tier1", 1, "Tier1 " * 50)
        _write_rule(rules_dir, "rule-tier2", 2, "Tier2 " * 50)

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "A [`rule-tier0`] B [`rule-tier1`] C [`rule-tier2`] D."
        results = measure_buffer(text)

        bytes_t0 = results["{0}"]["bytes"]
        bytes_t01 = results["{0,1}"]["bytes"]
        bytes_t012 = results["{0,1,2}"]["bytes"]
        bytes_full = results["full (None)"]["bytes"]

        assert bytes_t0 <= bytes_t01, "Tier-0-only must produce <= bytes as Tier-0+1"
        assert bytes_t01 <= bytes_t012, "Tier-0+1 must produce <= bytes as Tier-0+1+2"
        assert bytes_t012 == bytes_full, "Explicit {0,1,2} and full (None) should match for 3-tier rules"

    def test_all_four_configs_present(self, tmp_path, monkeypatch):
        """measure_buffer must always return all 4 tier_filter configurations."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        _write_rule(rules_dir, "rule-tier0", 0, "content")

        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "Simple [`rule-tier0`] text."
        results = measure_buffer(text)

        assert set(results.keys()) == {"full (None)", "{0,1,2}", "{0,1}", "{0}"}, (
            f"Unexpected config labels: {set(results.keys())}"
        )

    def test_no_markers_in_text(self, tmp_path, monkeypatch):
        """Plain text with no ref-key markers should return identical results for all configs."""
        monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))

        text = "No markers here, just plain text."
        results = measure_buffer(text)

        bytes_vals = {stats["bytes"] for stats in results.values()}
        unexpanded_vals = {stats["unexpanded_keys"] for stats in results.values()}

        assert len(bytes_vals) == 1, "All configs should produce same bytes for marker-free text"
        assert unexpanded_vals == {0}, "No markers means 0 unexpanded"
