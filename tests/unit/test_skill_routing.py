"""Tests for lib/skill_routing.py + ADR-050 dispatch integration.

Covers:
- Frontmatter extraction (with/without HTML comment prefix)
- `routing:` block parsing: full, partial, missing, malformed
- Type coercion / warning behaviour on wrong types
- `SkillRequirements.resolve_providers` precedence (preferred vs excluded)
- Dispatch integration:
  - providers_preferred overrides default cascade
  - providers_excluded drops from cascade
  - fallback_on_rate_limit=False stops cascade even on rate-limit
  - fallback_on_any_error=True advances on non-rate-limit Claude failure
  - budget_max_usd_per_call stops cascade once cap is reached
- Backward-compat: skill_requirements=None preserves legacy behaviour
- Real fixture: security-audit SKILL.md parses successfully

All dispatch tests use the same injection pattern as tests/unit/test_dispatch.py —
no real API calls.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib import dispatch as _d  # noqa: E402
from lib import skill_routing as _sr  # noqa: E402


# --------------------------------------------------------------------------- #
# Frontmatter extraction
# --------------------------------------------------------------------------- #


class TestFrontmatterExtraction(unittest.TestCase):
    def test_plain_frontmatter(self):
        text = "---\nname: foo\n---\n\nbody"
        fm = _sr._extract_frontmatter(text)
        self.assertEqual(fm, "name: foo")

    def test_frontmatter_after_html_comment(self):
        """SKILL.md files often start with `<!-- SCOPE: both -->` before `---`."""
        text = "<!-- SCOPE: both -->\n---\nname: foo\n---\nbody"
        fm = _sr._extract_frontmatter(text)
        self.assertEqual(fm, "name: foo")

    def test_no_frontmatter(self):
        text = "just a regular markdown file\nno fences\n"
        self.assertIsNone(_sr._extract_frontmatter(text))

    def test_unclosed_fence(self):
        text = "---\nname: foo\nno closing fence"
        self.assertIsNone(_sr._extract_frontmatter(text))

    def test_empty_file(self):
        self.assertIsNone(_sr._extract_frontmatter(""))


# --------------------------------------------------------------------------- #
# parse_routing_block
# --------------------------------------------------------------------------- #


class TestParseRoutingBlock(unittest.TestCase):
    def test_no_routing_key_returns_none(self):
        self.assertIsNone(_sr.parse_routing_block({"name": "foo"}))

    def test_routing_not_a_mapping_returns_none(self):
        self.assertIsNone(_sr.parse_routing_block({"routing": "not-a-dict"}))

    def test_full_routing_block(self):
        fm = {
            "routing": {
                "execution_profile": "frontier_reasoning",
                "tier": "frontier",
                "need_vision": False,
                "need_long_context": True,
                "providers_preferred": ["claude"],
                "providers_excluded": ["minimax", "qwen"],
                "fallback_on_rate_limit": False,
                "fallback_on_any_error": False,
                "budget_max_usd_per_call": 2.0,
            }
        }
        req = _sr.parse_routing_block(fm)
        self.assertIsNotNone(req)
        self.assertEqual(req.execution_profile, "frontier_reasoning")
        self.assertEqual(req.tier, "frontier")
        self.assertTrue(req.need_long_context)
        self.assertEqual(req.providers_preferred, ["claude"])
        self.assertEqual(req.providers_excluded, ["minimax", "qwen"])
        self.assertFalse(req.fallback_on_rate_limit)
        self.assertEqual(req.budget_max_usd_per_call, 2.0)

    def test_partial_routing_block_gets_defaults(self):
        req = _sr.parse_routing_block({"routing": {"tier": "cheap"}})
        self.assertEqual(req.tier, "cheap")
        self.assertEqual(req.providers_preferred, [])
        self.assertTrue(req.fallback_on_rate_limit)  # default
        self.assertFalse(req.fallback_on_any_error)  # default
        self.assertIsNone(req.budget_max_usd_per_call)

    def test_unknown_tier_warns_but_accepts(self):
        req = _sr.parse_routing_block({"routing": {"tier": "mystery-tier"}})
        self.assertIsNotNone(req)
        self.assertEqual(req.tier, "mystery-tier")

    def test_bad_providers_list_type_ignored(self):
        # Non-list gets dropped with warning, not crash
        req = _sr.parse_routing_block({"routing": {"providers_preferred": "claude"}})
        self.assertIsNotNone(req)
        self.assertEqual(req.providers_preferred, [])

    def test_malformed_budget_ignored(self):
        req = _sr.parse_routing_block({"routing": {"budget_max_usd_per_call": "not-a-number"}})
        self.assertIsNone(req.budget_max_usd_per_call)

    def test_bad_execution_profile_type_ignored(self):
        req = _sr.parse_routing_block({"routing": {"execution_profile": ["frontier_reasoning"]}})
        self.assertIsNotNone(req)
        self.assertIsNone(req.execution_profile)

    def test_non_string_providers_filtered(self):
        req = _sr.parse_routing_block(
            {"routing": {"providers_preferred": ["claude", 42, None, "qwen"]}}
        )
        self.assertEqual(req.providers_preferred, ["claude", "qwen"])


# --------------------------------------------------------------------------- #
# SkillRequirements.resolve_providers
# --------------------------------------------------------------------------- #


class TestResolveProviders(unittest.TestCase):
    def test_preferred_overrides_default(self):
        req = _sr.SkillRequirements(providers_preferred=["claude"])
        self.assertEqual(req.resolve_providers(["qwen", "claude"]), ["claude"])

    def test_excluded_removes_from_default(self):
        req = _sr.SkillRequirements(providers_excluded=["minimax"])
        self.assertEqual(
            req.resolve_providers(["qwen", "minimax", "claude"]),
            ["qwen", "claude"],
        )

    def test_excluded_applied_after_preferred(self):
        """Excluded removes from the preferred list too."""
        req = _sr.SkillRequirements(
            providers_preferred=["claude", "minimax"],
            providers_excluded=["minimax"],
        )
        self.assertEqual(req.resolve_providers(["qwen", "claude"]), ["claude"])

    def test_no_overrides_returns_default(self):
        req = _sr.SkillRequirements()
        self.assertEqual(req.resolve_providers(["qwen", "claude"]), ["qwen", "claude"])


# --------------------------------------------------------------------------- #
# load_skill_requirements (end-to-end, real file)
# --------------------------------------------------------------------------- #


class TestLoadSkillRequirements(unittest.TestCase):
    def test_file_missing_returns_none(self):
        self.assertIsNone(_sr.load_skill_requirements("/nonexistent/SKILL.md"))

    def test_no_frontmatter_returns_none(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("just markdown\n")
            path = f.name
        try:
            self.assertIsNone(_sr.load_skill_requirements(path))
        finally:
            Path(path).unlink()

    def test_malformed_yaml_returns_none(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\n: : : bad yaml : :\n---\nbody")
            path = f.name
        try:
            self.assertIsNone(_sr.load_skill_requirements(path))
        finally:
            Path(path).unlink()

    def test_security_audit_skill_parses(self):
        """Real fixture — security-audit SKILL.md must parse into valid SkillRequirements."""
        path = _REPO / "packages" / "quality-gates" / "skills" / "security-audit" / "SKILL.md"
        if not path.exists():
            self.skipTest("security-audit SKILL.md not present in this checkout")
        req = _sr.load_skill_requirements(path)
        self.assertIsNotNone(req, "security-audit must declare a routing block")
        self.assertEqual(req.tier, "frontier")
        self.assertIn("claude", req.providers_preferred)
        self.assertIn("minimax", req.providers_excluded)
        self.assertFalse(req.fallback_on_rate_limit)
        self.assertFalse(req.fallback_on_any_error)

    def test_sdd_explore_skill_parses(self):
        path = _REPO / "skills" / "sdd-explore" / "SKILL.md"
        if not path.exists():
            self.skipTest("sdd-explore SKILL.md not present")
        req = _sr.load_skill_requirements(path)
        self.assertIsNotNone(req)
        self.assertEqual(req.tier, "frontier")

    def test_sdd_resume_skill_parses(self):
        path = _REPO / "skills" / "sdd-resume" / "SKILL.md"
        if not path.exists():
            self.skipTest("sdd-resume SKILL.md not present")
        req = _sr.load_skill_requirements(path)
        self.assertIsNotNone(req)
        self.assertEqual(req.tier, "cheap")
        self.assertTrue(req.fallback_on_any_error)


class TestFindSkillMdPrecedence(unittest.TestCase):
    def test_repo_skill_wins_over_driver_and_canonical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo_skill = root / "skills" / "demo" / "SKILL.md"
            driver_skill = root / ".claude" / "skills" / "demo" / "SKILL.md"
            canonical_skill = root / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"
            repo_skill.parent.mkdir(parents=True)
            driver_skill.parent.mkdir(parents=True)
            canonical_skill.parent.mkdir(parents=True)
            repo_skill.write_text("# repo")
            driver_skill.write_text("# driver")
            canonical_skill.write_text("# canonical")
            self.assertEqual(_sr.find_skill_md("demo", root), repo_skill)

    def test_canonical_skill_wins_over_driver_projection_by_default(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            driver_skill = root / ".claude" / "skills" / "demo" / "SKILL.md"
            canonical_skill = root / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"
            driver_skill.parent.mkdir(parents=True)
            canonical_skill.parent.mkdir(parents=True)
            driver_skill.write_text("# driver")
            canonical_skill.write_text("# canonical")
            self.assertEqual(_sr.find_skill_md("demo", root), canonical_skill)

    def test_canonical_preference_can_win_over_driver_projection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            driver_skill = root / ".claude" / "skills" / "demo" / "SKILL.md"
            canonical_skill = root / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"
            driver_skill.parent.mkdir(parents=True)
            canonical_skill.parent.mkdir(parents=True)
            driver_skill.write_text("# driver")
            canonical_skill.write_text("# canonical")
            self.assertEqual(
                _sr.find_skill_md("demo", root, prefer_canonical=True),
                canonical_skill,
            )

    def test_canonical_fallback_used_when_other_surfaces_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            canonical_skill = root / ".cognitive-os" / "skills" / "cos" / "demo" / "SKILL.md"
            canonical_skill.parent.mkdir(parents=True)
            canonical_skill.write_text("# canonical")
            self.assertEqual(_sr.find_skill_md("demo", root), canonical_skill)

    def test_driver_projection_remains_supported_when_canonical_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            driver_skill = root / ".claude" / "skills" / "demo" / "SKILL.md"
            driver_skill.parent.mkdir(parents=True)
            driver_skill.write_text("# driver")
            self.assertEqual(_sr.find_skill_md("demo", root), driver_skill)


# --------------------------------------------------------------------------- #
# Dispatch integration (ADR-050 enforcement)
# --------------------------------------------------------------------------- #


def _success(provider_label: str, cost: float = 0.001):
    return {
        "success": True, "text": "ok", "tokens_in": 5, "tokens_out": 10,
        "cost_usd": cost, "error": "", "model": "test-model",
        "provider_label": provider_label,
    }


def _failure(provider_label: str, error: str, cost: float = 0.0):
    return {
        "success": False, "text": "", "tokens_in": 0, "tokens_out": 0,
        "cost_usd": cost, "error": error, "model": "test-model",
        "provider_label": provider_label,
    }


class TestDispatchSkillRequirements(unittest.TestCase):
    def test_preferred_overrides_default_cascade(self):
        """skill_requirements.providers_preferred rewrites the provider list."""
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            claude_executor=MagicMock(),
            skill_requirements={"providers_preferred": ["claude"]},
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _claude_fn=lambda p, m, e, t: _success("claude"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        # Only Claude should be in providers_requested; Qwen is overridden away
        self.assertEqual(sink[0]["providers_requested"], ["claude"])

    def test_excluded_removes_from_cascade(self):
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=["qwen", "minimax", "claude"],
            claude_executor=MagicMock(),
            skill_requirements={"providers_excluded": ["minimax"]},
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(sink[0]["providers_requested"], ["qwen", "claude"])

    def test_fallback_on_rate_limit_false_blocks_rate_limit_advance(self):
        """With fallback_on_rate_limit=False, rate-limit does NOT advance."""
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            skill_requirements={"fallback_on_rate_limit": False},
            _claude_fn=lambda p, m, e, t: _failure("claude", "You're out of extra usage"),
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertFalse(r.success)
        self.assertEqual(r.providers_tried, ["claude"])  # qwen NOT tried

    def test_fallback_on_any_error_advances_on_non_rate_limit(self):
        """With fallback_on_any_error=True, non-rate-limit Claude failure advances."""
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            skill_requirements={"fallback_on_any_error": True},
            _claude_fn=lambda p, m, e, t: _failure("claude", "connection refused"),
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.providers_tried, ["claude", "qwen"])

    def test_budget_cap_stops_cascade(self):
        """Once cumulative spend hits the cap, cascade stops before next attempt."""
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            skill_requirements={
                "fallback_on_any_error": True,
                "budget_max_usd_per_call": 0.005,
            },
            _claude_fn=lambda p, m, e, t: _failure("claude", "some error", cost=0.010),
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        # Claude spent $0.010 > cap $0.005 → Qwen never called
        self.assertFalse(r.success)
        self.assertEqual(r.providers_tried, ["claude"])

    def test_budget_under_cap_allows_fallback(self):
        """Spending below the cap still allows cascade to advance."""
        r = _d.dispatch(
            "hi", providers=["claude", "qwen"],
            claude_executor=MagicMock(),
            skill_requirements={
                "fallback_on_any_error": True,
                "budget_max_usd_per_call": 1.00,
            },
            _claude_fn=lambda p, m, e, t: _failure("claude", "error", cost=0.01),
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: None,
        )
        self.assertTrue(r.success)
        self.assertEqual(r.provider_used, "alibaba_qwen")

    def test_frontier_tier_shapes_cascade_when_provider_preference_absent(self):
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=None,
            claude_executor=MagicMock(),
            skill_requirements={"tier": "frontier"},
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _claude_fn=lambda p, m, e, t: _success("claude"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(sink[0]["providers_requested"], ["claude", "qwen"])
        self.assertEqual(sink[0]["execution_profile"]["id"], "frontier_reasoning")

    def test_explicit_provider_preference_wins_over_capability_profile(self):
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=None,
            claude_executor=MagicMock(),
            skill_requirements={"tier": "frontier", "providers_preferred": ["qwen", "claude"]},
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _claude_fn=lambda p, m, e, t: _success("claude"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(sink[0]["providers_requested"], ["qwen", "claude"])

    def test_none_skill_requirements_is_backward_compatible(self):
        """skill_requirements=None must behave identically to legacy dispatch."""
        sink_legacy: list[dict] = []
        sink_none: list[dict] = []
        # Legacy (no param)
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink_legacy.append(rec),
        )
        # Explicit None
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            skill_requirements=None,
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink_none.append(rec),
        )
        self.assertEqual(
            sink_legacy[0]["providers_requested"],
            sink_none[0]["providers_requested"],
        )
        # Legacy metric has no skill_routing block (or it's None)
        self.assertIsNone(sink_legacy[0].get("skill_routing"))
        self.assertIsNone(sink_none[0].get("skill_routing"))

    def test_skill_routing_block_appears_in_metric(self):
        """When skill_requirements is provided, metric record includes skill_routing."""
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            skill_requirements={
                "tier": "cheap",
                "providers_preferred": ["qwen"],
                "budget_max_usd_per_call": 0.50,
            },
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        sr = sink[0].get("skill_routing")
        self.assertIsNotNone(sr)
        self.assertEqual(sr["tier"], "cheap")
        self.assertEqual(sr["providers_preferred"], ["qwen"])
        self.assertEqual(sr["budget_max_usd_per_call"], 0.50)
        self.assertEqual(sink[0]["execution_profile"]["id"], "low_cost_bulk")

    def test_empty_skill_requirements_dict_is_noop(self):
        """An empty dict {} should behave like None — no routing applied."""
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            skill_requirements={},
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(sink[0]["providers_requested"], ["qwen", "claude"])
        self.assertIsNone(sink[0].get("skill_routing"))


# --------------------------------------------------------------------------- #
# to_dispatch_dict serialisation
# --------------------------------------------------------------------------- #


class TestToDispatchDict(unittest.TestCase):
    def test_roundtrip(self):
        req = _sr.SkillRequirements(
            tier="frontier",
            providers_preferred=["claude"],
            providers_excluded=["minimax"],
            fallback_on_rate_limit=False,
            budget_max_usd_per_call=1.5,
        )
        d = _sr.to_dispatch_dict(req)
        self.assertEqual(d["tier"], "frontier")
        self.assertEqual(d["execution_profile"], None)
        self.assertEqual(d["providers_preferred"], ["claude"])
        self.assertEqual(d["providers_excluded"], ["minimax"])
        self.assertFalse(d["fallback_on_rate_limit"])
        self.assertEqual(d["budget_max_usd_per_call"], 1.5)

    def test_to_dispatch_dict_is_dispatch_compatible(self):
        """to_dispatch_dict output must be directly usable as skill_requirements."""
        req = _sr.SkillRequirements(providers_preferred=["qwen"])
        sink: list[dict] = []
        _d.dispatch(
            "hi", providers=["qwen", "claude"],
            skill_requirements=_sr.to_dispatch_dict(req),
            _qwen_fn=lambda p, **k: _success("alibaba_qwen"),
            _metric_sink=lambda rec: sink.append(rec),
        )
        self.assertEqual(sink[0]["providers_requested"], ["qwen"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
