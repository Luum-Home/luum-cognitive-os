"""Behavioral tests for lib.ref_key_loader."""
from __future__ import annotations

import json

import pytest

from lib.ref_key_loader import _read_tier, expand, find_ref_keys, resolve


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


# ------------------------------------------------------------------ tier filtering


@pytest.fixture
def tiered_project(tmp_path, monkeypatch):
    """Isolated project with rules at different tiers."""
    monkeypatch.setenv("COGNITIVE_OS_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    rules = tmp_path / "rules"
    rules.mkdir()
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)

    # Tier-0 rule
    (rules / "trust-score.md").write_text("<!-- TIER: 0 -->\n# Trust Score\nTier0 content.\n")
    # Tier-1 rule (explicit frontmatter)
    (rules / "adaptive-bypass.md").write_text("<!-- TIER: 1 -->\n# Adaptive Bypass\nTier1 content.\n")
    # Tier-2 rule
    (rules / "aguara-integration.md").write_text("<!-- TIER: 2 -->\n# Aguara Integration\nTier2 content.\n")
    # Rule with NO frontmatter (should default to Tier-1)
    (rules / "no-frontmatter.md").write_text("# No Frontmatter\nDefault tier content.\n")

    return tmp_path


def test_expand_no_filter_unchanged(tiered_project):
    """tier_filter=None expands all rules — backward compatible."""
    text = "[`trust-score`] and [`aguara-integration`] and [`adaptive-bypass`]"
    out = expand(text, tier_filter=None)
    assert "Tier0 content." in out
    assert "Tier1 content." in out
    assert "Tier2 content." in out
    assert "[`" not in out  # no markers remain


def test_expand_tier_0_only(tiered_project):
    """With {0} filter, only Tier-0 rules expand; Tier-1 and Tier-2 markers remain."""
    text = "[`trust-score`] and [`adaptive-bypass`] and [`aguara-integration`]"
    out = expand(text, tier_filter={0})
    assert "Tier0 content." in out
    assert "[`adaptive-bypass`]" in out   # Tier-1 kept as marker
    assert "[`aguara-integration`]" in out  # Tier-2 kept as marker
    assert "Tier1 content." not in out
    assert "Tier2 content." not in out


def test_expand_tier_0_and_1(tiered_project):
    """With {0, 1} filter, Tier-0 and Tier-1 expand; Tier-2 markers remain."""
    text = "[`trust-score`] and [`adaptive-bypass`] and [`aguara-integration`]"
    out = expand(text, tier_filter={0, 1})
    assert "Tier0 content." in out
    assert "Tier1 content." in out
    assert "[`aguara-integration`]" in out  # Tier-2 kept as marker
    assert "Tier2 content." not in out


def test_expand_missing_frontmatter_defaults_to_tier_1(tiered_project):
    """Rules without TIER frontmatter are treated as Tier-1."""
    text = "[`no-frontmatter`]"
    # With tier_filter={0}: Tier-1 default should NOT expand
    out_t0 = expand(text, tier_filter={0})
    assert "[`no-frontmatter`]" in out_t0
    assert "Default tier content." not in out_t0

    # With tier_filter={0, 1}: Tier-1 default SHOULD expand
    out_t01 = expand(text, tier_filter={0, 1})
    assert "Default tier content." in out_t01


def test_expand_tier_2_explicit(tiered_project):
    """With {0, 1, 2} filter, Tier-2 rules also expand."""
    text = "[`aguara-integration`]"
    out = expand(text, tier_filter={0, 1, 2})
    assert "Tier2 content." in out
    assert "[`aguara-integration`]" not in out


def test_read_tier_returns_correct_values(tiered_project):
    """_read_tier() reads only line 1 and returns the tier integer."""
    from lib.ref_key_loader import _read_tier
    rules = tiered_project / "rules"
    assert _read_tier(rules / "trust-score.md") == 0
    assert _read_tier(rules / "adaptive-bypass.md") == 1
    assert _read_tier(rules / "aguara-integration.md") == 2
    # No frontmatter → default Tier-1
    assert _read_tier(rules / "no-frontmatter.md") == 1
    # Non-existent file → default Tier-1
    assert _read_tier(rules / "does-not-exist.md") == 1


def test_expand_tier_filter_expands_only_allowed_tiers(tmp_project):
    (tmp_project / "rules" / "tier-zero.md").write_text(
        "<!-- SCOPE: both -->\n<!-- TIER: 0 -->\n# Tier Zero\nAlways loaded.\n"
    )
    (tmp_project / "rules" / "tier-two.md").write_text(
        "<!-- SCOPE: both -->\n<!-- TIER: 2 -->\n# Tier Two\nLazy loaded.\n"
    )

    out = expand("[`tier-zero`] [`tier-two`]", tier_filter={0})

    assert "# Tier Zero" in out
    assert "# Tier Two" not in out
    assert "[`tier-two`]" in out


def test_expand_tier_filter_treats_missing_tier_as_tier_one(tmp_project):
    out = expand("[`trust-score`]", tier_filter={0})

    assert "# Trust Score" not in out
    assert out == "[`trust-score`]"


def test_expand_tier_filter_does_not_filter_overrides(tmp_project):
    out = expand(
        "[`trust-score`]",
        overrides={"trust-score": "OVERRIDDEN"},
        tier_filter={0},
    )

    assert out == "OVERRIDDEN"


def test_read_tier_defaults_to_one_when_frontmatter_is_missing(tmp_project):
    assert _read_tier(tmp_project / "rules" / "trust-score.md") == 1
