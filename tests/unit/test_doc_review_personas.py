"""Tests for lib/doc_review_personas.py and lib/persona_library.py.

All tests use tmp_path and a mocked dispatch_fn — no real API calls.
Covers:
- Persona library: loading, unknown-name error, default set
- Prompt builder composes role_brief + lens_questions
- Finding parser: TRUST_REPORT header + FINDING blocks + missing-tier floor
- Consolidation: dedup overlapping findings, merge reviewers, preserve severity
- Severity sort order (S1 < S2 < S3 < S4)
- Markdown renderer: sections exist and contain expected strings
- JSON renderer: schema-valid, parseable
- Empty docs_dir handled gracefully
- Dry-run produces mock plan without calling dispatch
- Parallel limit respected (max_parallel=1 serializes)
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO = Path(__file__).resolve().parent.parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from lib import doc_review_personas as drp  # noqa: E402
from lib import persona_library as pl  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_docs(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return root


def _mock_llm_response(findings: list[dict], score: int = 80) -> str:
    """Build a fake persona LLM response with TRUST_REPORT header + FINDINGs."""
    status = "HIGH" if score >= 90 else "MEDIUM" if score >= 70 else "LOW"
    lines = [
        f"TRUST_REPORT: SCORE={score} STATUS={status} EVIDENCE=2 UNCERTAINTIES=1",
        "---",
    ]
    for f in findings:
        lines.append("FINDING")
        lines.append(f"TIER: {f.get('tier', 'S3')}")
        lines.append(f"LOCATION: {f.get('location', 'docs/x.md')}")
        lines.append(f"WHAT: {f.get('what', 'something')}")
        lines.append(f"WHY: {f.get('why', 'reasons')}")
        lines.append(f"RECOMMENDATION: {f.get('recommendation', 'fix it')}")
    return "\n".join(lines)


def _fake_dispatch_factory(findings_per_persona: dict[str, list[dict]]):
    """Build a dispatch_fn that returns canned responses keyed by persona name.
    Persona name is detected via the role_brief substring inside the prompt.
    """
    def fn(prompt: str, model: str) -> dict:
        for name, findings in findings_per_persona.items():
            # Match by a stable substring of role_brief
            if f"ROLE BRIEF ({name})" in prompt:
                return {
                    "success": True,
                    "text": _mock_llm_response(findings),
                    "cost_usd": 0.0001,
                    "provider_used": "mock",
                    "error": "",
                }
        return {
            "success": True,
            "text": _mock_llm_response([{"tier": "S4", "what": "default"}]),
            "cost_usd": 0.0001,
            "provider_used": "mock",
            "error": "",
        }
    return fn


# ---------------------------------------------------------------------------
# Persona library
# ---------------------------------------------------------------------------

class TestPersonaLibrary(unittest.TestCase):
    def test_all_builtin_personas_load(self):
        names = pl.list_personas()
        self.assertIn("cfo", names)
        self.assertIn("tech_lead", names)
        self.assertIn("commercial", names)
        self.assertIn("new_dev_onboarding", names)
        self.assertIn("editor_qa", names)
        for n in names:
            p = pl.get_persona(n)
            self.assertGreaterEqual(len(p.role_brief.split()), 30,
                                    f"{n} role_brief too short")
            self.assertGreaterEqual(len(p.lens_questions), 5,
                                    f"{n} should have >=5 lens_questions")

    def test_unknown_persona_raises(self):
        with self.assertRaises(KeyError):
            pl.get_persona("does_not_exist")

    def test_persona_name_case_insensitive(self):
        self.assertEqual(pl.get_persona("CFO").name, "cfo")
        self.assertEqual(pl.get_persona("Tech-Lead").name, "tech_lead")

    def test_default_persona_set_has_5(self):
        s = pl.default_persona_set()
        self.assertEqual(len(s), 5)

    def test_build_prompt_contains_role_brief_and_questions(self):
        p = pl.get_persona("editor_qa")
        prompt = pl.build_persona_prompt(p, "fake docs corpus")
        self.assertIn(p.role_brief, prompt)
        for q in p.lens_questions:
            self.assertIn(q, prompt)
        self.assertIn("fake docs corpus", prompt)
        self.assertIn("TRUST_REPORT:", prompt)
        self.assertIn("FINDING", prompt)


# ---------------------------------------------------------------------------
# load_docs
# ---------------------------------------------------------------------------

class TestLoadDocs(unittest.TestCase):
    def test_load_docs_concatenates_markdown(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = _write_docs(Path(td), {
                "a.md": "# A\n\nContenido A",
                "sub/b.md": "# B\n\nContenido B",
                "skip.json": "{}",  # non-matching extension
            })
            corpus, files = drp.load_docs(root)
            self.assertIn("FILE: a.md", corpus)
            self.assertIn("FILE: sub/b.md", corpus)
            self.assertNotIn("skip.json", corpus)
            self.assertEqual(len(files), 2)

    def test_load_docs_missing_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            drp.load_docs(Path("/nonexistent/path/xyz_doc_review_test"))


# ---------------------------------------------------------------------------
# parse_findings
# ---------------------------------------------------------------------------

class TestParseFindings(unittest.TestCase):
    def test_parses_trust_header_and_findings(self):
        raw = _mock_llm_response([
            {"tier": "S1", "location": "docs/a.md", "what": "broken"},
            {"tier": "S3", "location": "docs/b.md", "what": "minor"},
        ], score=85)
        findings, score, status = drp.parse_findings(raw, "editor_qa")
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0].tier, "S1")
        self.assertEqual(findings[1].tier, "S3")
        self.assertEqual(score, 85)
        self.assertEqual(status, "MEDIUM")
        self.assertEqual(findings[0].reviewers, ["editor_qa"])

    def test_missing_tier_uses_default_floor(self):
        raw = (
            "TRUST_REPORT: SCORE=70 STATUS=MEDIUM EVIDENCE=1 UNCERTAINTIES=1\n"
            "---\n"
            "FINDING\n"
            "LOCATION: docs/x.md\n"
            "WHAT: no tier given\n"
        )
        findings, _, _ = drp.parse_findings(raw, "p1", default_severity_floor="S3")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].tier, "S3")

    def test_invalid_tier_falls_back_to_floor(self):
        raw = (
            "FINDING\nTIER: S9\nLOCATION: x\nWHAT: bad\n"
        )
        findings, _, _ = drp.parse_findings(raw, "p1", default_severity_floor="S2")
        self.assertEqual(findings[0].tier, "S2")

    def test_no_findings_returns_empty_list(self):
        raw = "just some text with no markers"
        findings, _, _ = drp.parse_findings(raw, "p1")
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# consolidate
# ---------------------------------------------------------------------------

class TestConsolidate(unittest.TestCase):
    def test_dedupes_same_location_and_topic(self):
        r1 = drp.PersonaResult(persona="a", success=True, findings=[
            drp.Finding(tier="S2", location="docs/x.md", what="broken link in intro",
                        why="", recommendation="", reviewers=["a"]),
        ])
        r2 = drp.PersonaResult(persona="b", success=True, findings=[
            drp.Finding(tier="S1", location="docs/x.md", what="broken link in intro",
                        why="", recommendation="", reviewers=["b"]),
        ])
        merged = drp.consolidate([r1, r2])
        self.assertEqual(len(merged), 1)
        # Highest severity wins
        self.assertEqual(merged[0].tier, "S1")
        # Reviewers unioned
        self.assertEqual(sorted(merged[0].reviewers), ["a", "b"])

    def test_keeps_distinct_findings(self):
        r1 = drp.PersonaResult(persona="a", success=True, findings=[
            drp.Finding(tier="S2", location="docs/x.md", what="broken link",
                        why="", recommendation="", reviewers=["a"]),
        ])
        r2 = drp.PersonaResult(persona="b", success=True, findings=[
            drp.Finding(tier="S2", location="docs/y.md", what="typo",
                        why="", recommendation="", reviewers=["b"]),
        ])
        merged = drp.consolidate([r1, r2])
        self.assertEqual(len(merged), 2)

    def test_sorted_by_severity_then_location(self):
        findings = [
            drp.Finding(tier="S3", location="z.md", what="w3", why="", recommendation=""),
            drp.Finding(tier="S1", location="a.md", what="w1", why="", recommendation=""),
            drp.Finding(tier="S2", location="m.md", what="w2", why="", recommendation=""),
        ]
        r = drp.PersonaResult(persona="x", success=True, findings=findings)
        merged = drp.consolidate([r])
        self.assertEqual([f.tier for f in merged], ["S1", "S2", "S3"])


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

class TestRendering(unittest.TestCase):
    def _make_report(self):
        findings = [
            drp.Finding(tier="S1", location="docs/a.md", what="big problem",
                        why="blocks release", recommendation="fix now",
                        reviewers=["cfo", "tech_lead"]),
            drp.Finding(tier="S3", location="docs/b.md", what="small typo",
                        why="aesthetics", recommendation="sed -i ...",
                        reviewers=["editor_qa"]),
        ]
        pr = [drp.PersonaResult(persona="cfo", success=True, findings=findings[:1],
                                trust_score=75, trust_status="MEDIUM",
                                cost_usd=0.0005, provider_used="mock")]
        return drp.ReviewReport(
            docs_dir="/tmp/docs", docs_files=["a.md", "b.md"],
            persona_results=pr, consolidated=findings, total_cost_usd=0.0005,
        )

    def test_markdown_renders_sections(self):
        md = drp.render_markdown(self._make_report())
        self.assertIn("# Doc Review — Multi-Persona", md)
        self.assertIn("Críticos (S1 BLOCKER)", md)
        self.assertIn("Menores (S3 SUGGESTION)", md)
        self.assertIn("docs/a.md", md)
        self.assertIn("big problem", md)
        self.assertIn("cfo, tech_lead", md)  # reviewers attribution

    def test_json_renders_valid_schema(self):
        js = drp.render_json(self._make_report())
        payload = json.loads(js)  # must parse
        self.assertIn("severity_counts", payload)
        self.assertEqual(payload["severity_counts"]["S1"], 1)
        self.assertEqual(payload["severity_counts"]["S3"], 1)
        self.assertEqual(len(payload["consolidated"]), 2)
        self.assertEqual(payload["consolidated"][0]["tier"], "S1")


# ---------------------------------------------------------------------------
# Full pipeline with mocked dispatch
# ---------------------------------------------------------------------------

class TestRunReview(unittest.TestCase):
    def test_empty_docs_dir_handled(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            report = drp.run_review(
                docs_dir=Path(td),
                personas=[pl.get_persona("editor_qa")],
                dry_run=False,
                dispatch_fn=lambda p, m: {"success": True, "text": "",
                                          "cost_usd": 0, "provider_used": "",
                                          "error": ""},
            )
            self.assertEqual(len(report.docs_files), 0)
            # One S4 review-incomplete finding per persona
            self.assertEqual(len(report.consolidated), 1)
            self.assertEqual(report.consolidated[0].tier, "S4")

    def test_dry_run_skips_llm(self):
        import tempfile
        calls = {"n": 0}

        def should_not_be_called(p, m):
            calls["n"] += 1
            return {"success": True, "text": "", "cost_usd": 0,
                    "provider_used": "", "error": ""}

        with tempfile.TemporaryDirectory() as td:
            _write_docs(Path(td), {"a.md": "some content"})
            report = drp.run_review(
                docs_dir=Path(td),
                personas=[pl.get_persona("editor_qa"), pl.get_persona("cfo")],
                dry_run=True,
                dispatch_fn=should_not_be_called,
            )
            self.assertEqual(calls["n"], 0)
            self.assertEqual(len(report.persona_results), 2)
            for r in report.persona_results:
                self.assertEqual(len(r.findings), 1)
                self.assertEqual(r.findings[0].tier, "S4")

    def test_full_pipeline_with_mocked_dispatch(self):
        import tempfile
        mock_dispatch = _fake_dispatch_factory({
            "editor_qa": [
                {"tier": "S1", "location": "docs/a.md",
                 "what": "broken link in intro", "why": "kills quickstart",
                 "recommendation": "fix href"},
            ],
            "cfo": [
                {"tier": "S2", "location": "docs/budget.md",
                 "what": "dates don't close", "why": "week 4 vs week 6",
                 "recommendation": "reconcile schedule"},
            ],
        })
        with tempfile.TemporaryDirectory() as td:
            _write_docs(Path(td), {
                "a.md": "# Intro\n[link](broken)",
                "budget.md": "Sprint ends week 4. Sprint starts week 6.",
            })
            report = drp.run_review(
                docs_dir=Path(td),
                personas=[pl.get_persona("editor_qa"), pl.get_persona("cfo")],
                dispatch_fn=mock_dispatch,
                max_parallel=2,
            )
            self.assertEqual(len(report.persona_results), 2)
            self.assertTrue(all(r.success for r in report.persona_results))
            self.assertEqual(len(report.consolidated), 2)
            counts = report.severity_counts()
            self.assertEqual(counts["S1"], 1)
            self.assertEqual(counts["S2"], 1)
            # Markdown is renderable
            md = drp.render_markdown(report)
            self.assertIn("broken link in intro", md)

    def test_max_parallel_1_serializes(self):
        """Smoke: max_parallel=1 still completes successfully.
        We can't directly observe serialization from outside, but we can
        verify the cap does not break correctness.
        """
        import tempfile
        mock = _fake_dispatch_factory({})
        with tempfile.TemporaryDirectory() as td:
            _write_docs(Path(td), {"a.md": "content"})
            report = drp.run_review(
                docs_dir=Path(td),
                personas=pl.default_persona_set(),
                dispatch_fn=mock,
                max_parallel=1,
            )
            self.assertEqual(len(report.persona_results), 5)

    def test_persona_failure_isolated(self):
        import tempfile

        def flaky(prompt, model):
            if "ROLE BRIEF (cfo)" in prompt:
                return {"success": False, "text": "", "cost_usd": 0,
                        "provider_used": "mock", "error": "simulated failure"}
            return {"success": True,
                    "text": _mock_llm_response([{"tier": "S3", "what": "ok"}]),
                    "cost_usd": 0, "provider_used": "mock", "error": ""}

        with tempfile.TemporaryDirectory() as td:
            _write_docs(Path(td), {"a.md": "content"})
            report = drp.run_review(
                docs_dir=Path(td),
                personas=[pl.get_persona("cfo"), pl.get_persona("editor_qa")],
                dispatch_fn=flaky,
                max_parallel=2,
            )
            by_name = {r.persona: r for r in report.persona_results}
            self.assertFalse(by_name["cfo"].success)
            self.assertTrue(by_name["editor_qa"].success)
            # Editor still produced findings even though CFO failed
            self.assertGreater(len(by_name["editor_qa"].findings), 0)


if __name__ == "__main__":
    unittest.main()
