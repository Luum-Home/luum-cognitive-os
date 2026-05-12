from __future__ import annotations

from lib.validation_lanes import recommend_lane


def test_docs_only_diff_recommends_fast_lane() -> None:
    rec = recommend_lane(["docs/02-Decisions/adrs/ADR-123-operational-stability-friction-reduction.md"])

    assert rec.recommended_lane == "fast"
    assert "docs-only" in " ".join(rec.rationale)


def test_runtime_script_diff_recommends_landing_lane() -> None:
    rec = recommend_lane(["scripts/cos_repair.py"])

    assert rec.recommended_lane == "landing"
    assert "script" in " ".join(rec.rationale)


def test_hook_diff_recommends_laptop_lane() -> None:
    rec = recommend_lane(["hooks/destructive-git-blocker.sh"])

    assert rec.recommended_lane == "laptop"
