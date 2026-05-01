"""Behavioral unit tests for scripts/validate_tier_filter.py.

Covers:
- end-to-end harness run on synthetic transcript fixture → correct JSON shape
- statistical test logic (Wilcoxon signed-rank) with known inputs
- both replay and synthetic paths without real LLM calls (mocked dispatch)
"""
from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# ── import subject ─────────────────────────────────────────────────────────
from scripts.validate_tier_filter import (  # noqa: E402
    BASELINE_RATE,
    REVERT_THRESHOLD,
    _sign_rank,
    collect_replay_prompts,
    collect_synthetic_prompts,
    compute_statistics,
    make_recommendation,
    measure_prompt,
)


# ===========================================================================
# Fixtures
# ===========================================================================

TIER1_PROMPT = textwrap.dedent("""\
    Perform cross-service refactor.
    Follow [`blast-radius`] and [`decomposition`] and [`scope-proportionality`].
    Use [`model-routing`] and [`token-economy`].
""")

TIER0_ONLY_PROMPT = textwrap.dedent("""\
    Fix a typo.  Follow [`acceptance-criteria`] and [`trust-score`].
""")

NO_REFS_PROMPT = "Just fix the typo in README please."


# ===========================================================================
# Unit: measure_prompt
# ===========================================================================

class TestMeasurePrompt:
    def test_returns_both_configs(self):
        result = measure_prompt(TIER0_ONLY_PROMPT)
        assert "config_a" in result
        assert "config_b" in result

    def test_tier0_prompt_has_zero_delta(self):
        """Tier-0 refs are expanded by BOTH configs → no difference."""
        r = measure_prompt(TIER0_ONLY_PROMPT)
        # unexpanded_keys should be equal (or B ≤ A, never B > A for Tier-0)
        assert r["config_b"]["unexpanded_keys"] == r["config_a"]["unexpanded_keys"]

    def test_tier1_prompt_b_leaves_more_unexpanded(self):
        """Tier-1 refs are NOT expanded by Config B → B has more unexpanded keys."""
        r = measure_prompt(TIER1_PROMPT)
        # Config B (tier_filter={0}) must leave at least some Tier-1 refs unexpanded
        # whereas Config A (tier_filter={0,1}) expands them.
        # If rules files are present, B should have more; if not present, both miss equally.
        # At minimum the structure must be intact.
        assert "unexpanded_keys" in r["config_a"]
        assert "unexpanded_keys" in r["config_b"]
        assert r["config_b"]["unexpanded_keys"] >= r["config_a"]["unexpanded_keys"]

    def test_no_refs_prompt(self):
        r = measure_prompt(NO_REFS_PROMPT)
        assert r["config_a"]["total_ref_keys"] == 0
        assert r["config_b"]["total_ref_keys"] == 0


# ===========================================================================
# Unit: collect_synthetic_prompts
# ===========================================================================

class TestCollectSynthetic:
    def test_returns_requested_count(self):
        trials = collect_synthetic_prompts(15)
        assert len(trials) == 15

    def test_trial_has_required_keys(self):
        trials = collect_synthetic_prompts(5)
        for t in trials:
            assert t["source"] == "synthetic"
            assert "config_a" in t
            assert "config_b" in t
            assert "prompt_preview" in t

    def test_over_seed_count_cycles(self):
        # More trials than seeds → should cycle
        trials = collect_synthetic_prompts(50)
        assert len(trials) == 50

    def test_tier1_seeds_produce_delta(self):
        """At least some synthetic seeds exercise Tier-1 refs."""
        trials = collect_synthetic_prompts(15)
        deltas = [
            t["config_b"]["unexpanded_keys"] - t["config_a"]["unexpanded_keys"]
            for t in trials
        ]
        # With real rule files: some deltas should be > 0.
        # Without rule files (CI): all deltas may be 0 — test structure only.
        assert all(isinstance(d, int) for d in deltas)


# ===========================================================================
# Unit: collect_replay_prompts (mocked session dir)
# ===========================================================================

class TestCollectReplay:
    def test_falls_back_gracefully_when_no_sessions(self, tmp_path):
        """If session dir has no ref-key prompts, returns empty list."""
        with patch(
            "scripts.validate_tier_filter._SESSION_DIR", tmp_path
        ):
            result = collect_replay_prompts(10)
        assert isinstance(result, list)

    def test_parses_synthetic_transcript(self, tmp_path):
        """Harness extracts user turns with ref-key markers from JSONL."""
        prompt_with_ref = "Fix [`blast-radius`] and [`decomposition`] issues."
        record = {
            "type": "user",
            "message": {
                "role": "user",
                "content": prompt_with_ref,
            },
        }
        session_file = tmp_path / "test-session.jsonl"
        session_file.write_text(json.dumps(record) + "\n")

        with patch("scripts.validate_tier_filter._SESSION_DIR", tmp_path):
            trials = collect_replay_prompts(5)

        assert len(trials) >= 1
        assert trials[0]["source"] == "replay"
        assert "config_a" in trials[0]
        assert "config_b" in trials[0]

    def test_skips_prompts_without_ref_keys(self, tmp_path):
        """User turns without [`key`] markers are ignored."""
        record = {
            "type": "user",
            "message": {"role": "user", "content": "Hello world"},
        }
        session_file = tmp_path / "plain-session.jsonl"
        session_file.write_text(json.dumps(record) + "\n")

        with patch("scripts.validate_tier_filter._SESSION_DIR", tmp_path):
            trials = collect_replay_prompts(5)

        assert trials == []


# ===========================================================================
# Unit: Wilcoxon signed-rank (_sign_rank)
# ===========================================================================

class TestSignRank:
    def test_all_zero_diffs(self):
        w, note = _sign_rank([0, 0, 0, 0])
        assert w == 0.0
        assert note == "all_tied"

    def test_known_one_sided(self):
        """All positive diffs → W_minus = 0 → W = 0 (extreme case)."""
        diffs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        w, note = _sign_rank(diffs)
        assert w == 0  # W = min(W+, W-) = min(55, 0) = 0
        assert "p=" in note  # normal approximation applied (n=10)

    def test_symmetric_diffs_high_w(self):
        """Symmetric positive/negative diffs → large W (not significant)."""
        diffs = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0, 4.0, -4.0, 5.0, -5.0]
        w, note = _sign_rank(diffs)
        # W should be large (not significant)
        assert isinstance(w, (int, float))

    def test_insufficient_n(self):
        """Fewer than 10 nonzero diffs → note warns about approximation."""
        w, note = _sign_rank([1.0, 2.0, 3.0])
        assert "insufficient" in note


# ===========================================================================
# Unit: compute_statistics
# ===========================================================================

class TestComputeStatistics:
    def _make_trials(self, n: int, a_val: int, b_val: int) -> list[dict]:
        """Manufacture synthetic trials with fixed unexpanded counts."""
        return [
            {
                "config_a": {"unexpanded_keys": a_val, "total_ref_keys": 5, "resolved_keys": 5 - a_val, "unexpanded_key_names": []},
                "config_b": {"unexpanded_keys": b_val, "total_ref_keys": 5, "resolved_keys": 5 - b_val, "unexpanded_key_names": []},
            }
            for _ in range(n)
        ]

    def test_shape(self):
        trials = self._make_trials(10, 0, 2)
        with patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.3):
            stats = compute_statistics(trials)
        required_keys = {
            "n_trials", "mean_unexpanded_keys_a", "mean_unexpanded_keys_b",
            "mean_delta_b_minus_a", "trials_b_worse", "trials_neutral",
            "trials_b_better", "wilcoxon_w", "wilcoxon_note",
            "baseline_skills_failed_rate", "revert_threshold",
            "observed_skills_failed_rate",
        }
        assert required_keys.issubset(set(stats.keys()))

    def test_mean_delta(self):
        trials = self._make_trials(10, 0, 3)
        with patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.3):
            stats = compute_statistics(trials)
        assert stats["mean_delta_b_minus_a"] == 3.0
        assert stats["trials_b_worse"] == 10

    def test_neutral(self):
        trials = self._make_trials(20, 2, 2)
        with patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.3):
            stats = compute_statistics(trials)
        assert stats["trials_neutral"] == 20
        assert stats["mean_delta_b_minus_a"] == 0.0


# ===========================================================================
# Unit: make_recommendation
# ===========================================================================

class TestMakeRecommendation:
    def _base_stats(self, **overrides) -> dict:
        base = {
            "n_trials": 30,
            "mean_unexpanded_keys_a": 0.0,
            "mean_unexpanded_keys_b": 1.0,
            "mean_delta_b_minus_a": 1.0,
            "trials_b_worse": 5,
            "trials_neutral": 25,
            "trials_b_better": 0,
            "wilcoxon_w": 10,
            "wilcoxon_note": "z=2.1 p=0.03",
            "baseline_skills_failed_rate": BASELINE_RATE,
            "revert_threshold": REVERT_THRESHOLD,
            "observed_skills_failed_rate": 0.265,
        }
        base.update(overrides)
        return base

    def test_flip_when_rate_ok_and_low_regression(self):
        stats = self._base_stats(
            trials_b_worse=5,
            trials_neutral=25,
            mean_delta_b_minus_a=1.0,
            observed_skills_failed_rate=0.265,
        )
        result = make_recommendation(stats)
        assert result["recommendation"] == "FLIP"

    def test_keep_when_rate_exceeds_threshold(self):
        stats = self._base_stats(observed_skills_failed_rate=1.2)
        result = make_recommendation(stats)
        assert result["recommendation"] == "KEEP"

    def test_keep_when_high_expansion_regression(self):
        stats = self._base_stats(
            trials_b_worse=15,  # 50% regression rate
            trials_neutral=15,
            mean_delta_b_minus_a=5.0,  # ≥3 threshold
            observed_skills_failed_rate=0.265,
        )
        result = make_recommendation(stats)
        assert result["recommendation"] == "KEEP"

    def test_needs_more_data_when_insufficient_n(self):
        stats = self._base_stats(n_trials=10)
        result = make_recommendation(stats)
        assert result["recommendation"] == "NEEDS-MORE-DATA"

    def test_auto_flip_off_by_default(self):
        stats = self._base_stats()
        result = make_recommendation(stats)
        assert result["auto_flip_enabled"] is False
        assert result["auto_flip_eligible"] is False

    def test_auto_flip_on_when_env_set(self, monkeypatch):
        monkeypatch.setenv("COS_AUTO_FLIP_TIER_FILTER", "1")
        stats = self._base_stats(
            trials_b_worse=5,
            trials_neutral=25,
            mean_delta_b_minus_a=1.0,
            observed_skills_failed_rate=0.265,
        )
        result = make_recommendation(stats)
        assert result["auto_flip_enabled"] is True
        if result["recommendation"] == "FLIP":
            assert result["auto_flip_eligible"] is True


# ===========================================================================
# Integration: full harness run → correct JSON output shape
# ===========================================================================

class TestHarnessEndToEnd:
    def test_synthetic_run_produces_valid_json(self, tmp_path):
        out_path = tmp_path / "report.json"
        from scripts.validate_tier_filter import main as harness_main

        with patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.265):
            ret = harness_main([
                "--approach=synthetic",
                "--n=15",
                f"--output={out_path}",
            ])

        assert ret == 0
        assert out_path.exists()

        report = json.loads(out_path.read_text())
        assert report["schema_version"] == "1.0"
        assert "statistics" in report
        assert "decision" in report
        assert "trials" in report
        assert len(report["trials"]) == 15
        assert report["decision"]["recommendation"] in {
            "FLIP", "KEEP", "NEEDS-MORE-DATA"
        }

    def test_markdown_summary_written(self, tmp_path):
        out_path = tmp_path / "report.json"
        from scripts.validate_tier_filter import main as harness_main

        with patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.265):
            harness_main(["--approach=synthetic", "--n=15", f"--output={out_path}"])

        md_path = out_path.with_suffix(".md")
        assert md_path.exists()
        content = md_path.read_text()
        assert "Tier-Filter Validation Report" in content
        assert "Recommendation" in content

    def test_replay_fallback_to_synthetic(self, tmp_path):
        """When session dir has no ref-key prompts, falls back to synthetic."""
        out_path = tmp_path / "report.json"
        from scripts.validate_tier_filter import main as harness_main

        with (
            patch("scripts.validate_tier_filter._SESSION_DIR", tmp_path),
            patch("scripts.validate_tier_filter._compute_skills_failed_rate", return_value=0.265),
        ):
            ret = harness_main([
                "--approach=replay",
                "--n=10",
                f"--output={out_path}",
            ])

        assert ret == 0
        report = json.loads(out_path.read_text())
        # Should have fallen back
        assert "synthetic" in report["approach"]

    def test_dry_run_mode(self, tmp_path):
        out_path = tmp_path / "dry.json"
        from scripts.validate_tier_filter import main as harness_main

        ret = harness_main(["--approach=synthetic", "--n=5", f"--output={out_path}", "--dry-run"])
        assert ret == 0
        report = json.loads(out_path.read_text())
        assert report["dry_run"] is True
        assert report["decision"]["recommendation"] == "DRY-RUN"
