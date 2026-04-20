"""Behavioral tests for lib.ref_key_loader."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.ref_key_loader import expand, find_ref_keys, resolve


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Isolated project with rules/ and metrics/ dirs."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    (tmp_path / "rules").mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    (tmp_path / "rules" / "trust-score.md").write_text("# Trust Score\nRule body.\n")
    (tmp_path / "rules" / "so-slo.md").write_text("# SO SLOs\nTable here.\n")
    return tmp_path


# ------------------------------------------------------------------ find_ref_keys


def test_find_ref_keys_extracts_markers():
    text = "See [`trust-score`] and [`so-slo`] and [`nothing`]."
    assert find_ref_keys(text) == ["trust-score", "so-slo", "nothing"]


def test_find_ref_keys_deduplicates_preserving_order():
    text = "[`a`] foo [`b`] bar [`a`] baz"
    assert find_ref_keys(text) == ["a", "b"]


def test_find_ref_keys_empty_or_no_matches():
    assert find_ref_keys("") == []
    assert find_ref_keys("no markers at all") == []
    assert find_ref_keys(None) == []  # type: ignore[arg-type]


def test_find_ref_keys_rejects_markers_with_whitespace():
    # Backtick-wrapped but contains a space — not a valid ref-key.
    assert find_ref_keys("[`has space`]") == []
    # Hyphens and digits are fine.
    assert find_ref_keys("[`kebab-case-9`]") == ["kebab-case-9"]


# ------------------------------------------------------------------ resolve


def test_resolve_returns_content_for_existing_rules(tmp_project):
    text = "Reference [`trust-score`] and [`so-slo`]."
    out = resolve(text)
    assert "Trust Score" in (out["trust-score"] or "")
    assert "SO SLOs" in (out["so-slo"] or "")


def test_resolve_returns_none_for_missing_key(tmp_project):
    out = resolve("[`does-not-exist`]")
    assert out == {"does-not-exist": None}


def test_resolve_respects_overrides(tmp_project):
    out = resolve("[`trust-score`]", overrides={"trust-score": "OVERRIDDEN"})
    assert out["trust-score"] == "OVERRIDDEN"


def test_resolve_logs_miss_to_jsonl(tmp_project):
    miss_log = tmp_project / ".cognitive-os" / "metrics" / "ref-key-misses.jsonl"
    assert not miss_log.exists()
    resolve("[`missing-one`]")
    assert miss_log.exists()
    rows = [
        json.loads(line)
        for line in miss_log.read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 1
    assert rows[0]["source"] == "ref_key_loader"
    assert rows[0]["event_type"] == "miss"
    assert rows[0]["payload"]["key"] == "missing-one"


# ------------------------------------------------------------------ expand


def test_expand_substitutes_hits_and_preserves_misses(tmp_project):
    text = "start [`trust-score`] middle [`missing-x`] end"
    out = expand(text)
    assert "# Trust Score" in out
    assert "Rule body." in out
    # Miss preserved verbatim.
    assert "[`missing-x`]" in out


def test_expand_with_fence_wraps_content(tmp_project):
    out = expand("A [`trust-score`] B", fence="\n---\n")
    assert "\n---\n# Trust Score" in out
    assert "Rule body.\n\n---\n B" in out


def test_expand_idempotent_when_no_markers_remain(tmp_project):
    # After first pass, no markers remain; second pass should not change anything.
    text = "[`trust-score`]"
    once = expand(text)
    twice = expand(once)
    assert once == twice


def test_expand_max_depth_zero_is_noop(tmp_project):
    text = "[`trust-score`]"
    out = expand(text, max_depth=0)
    assert out == text


def test_expand_does_not_recurse_past_max_depth(tmp_project):
    # A rule whose content itself contains a ref-key.
    (tmp_project / "rules" / "meta.md").write_text("Meta starts — [`trust-score`] — meta ends.")
    text = "[`meta`]"
    depth1 = expand(text, max_depth=1)
    # depth=1 expands meta but NOT the nested trust-score marker.
    assert "[`trust-score`]" in depth1
    assert "Meta starts" in depth1
    # depth=2 expands both layers.
    depth2 = expand(text, max_depth=2)
    assert "[`trust-score`]" not in depth2
    assert "# Trust Score" in depth2
