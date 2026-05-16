# SCOPE: os-only
"""ADR-296 — language-agnostic semantic skill routing.

The live-embedding tests are gated by the ``semantic_routing`` marker so
they can be skipped in environments where ``fastembed`` is unavailable
(it ships a ~220 MB ONNX model on first use). Pure-Python tests for the
loader, kill switch, and disk cache stay unmarked.
"""
from __future__ import annotations

import time

import pytest

from lib import semantic_skill_matcher as sm
from lib.semantic_skill_matcher import (
    SemanticMatch,
    SemanticSkillMatcher,
    load_skill_metadata,
)

# Importable only when fastembed is installed. Tests guarded by this flag
# additionally carry the ``semantic_routing`` marker so the suite can be
# trimmed via ``-m "not semantic_routing"`` in resource-constrained CI.
try:
    import fastembed  # type: ignore  # noqa: F401

    FASTEMBED_AVAILABLE = True
except Exception:
    FASTEMBED_AVAILABLE = False

# Mark everything live as ``semantic_routing``. The conftest auto-marker
# pipeline injects the lane marker; we add the live-only marker manually.
live = pytest.mark.semantic_routing


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_router():
    """Real SkillRouter against the on-disk catalog (all 196 skills)."""
    from lib.skill_router import SkillRouter

    return SkillRouter()


@pytest.fixture(scope="module")
def matcher(real_router):
    metadata = load_skill_metadata(real_router._skill_md_paths)
    m = SemanticSkillMatcher.from_routing_table(real_router._routing_table, metadata)
    return m


# ---------------------------------------------------------------------------
# Pure-Python (no live model)
# ---------------------------------------------------------------------------

def test_kill_switch_short_circuits(monkeypatch, tmp_path):
    """COS_DISABLE_SEMANTIC_ROUTING=1 returns [] without loading any model."""
    matcher_local = SemanticSkillMatcher(
        indices=[
            sm._SkillIndex(
                skill_name="product-answer",
                invoke_command="/product-answer",
                description="Answer COS product questions",
            )
        ],
        cache_dir=tmp_path,
    )
    monkeypatch.setenv("COS_DISABLE_SEMANTIC_ROUTING", "1")
    assert matcher_local.match("can this help me as a developer?") == []


def test_load_skill_metadata_parses_real_catalog(real_router):
    meta = load_skill_metadata(real_router._skill_md_paths)
    # Sanity: catalog is non-trivial and product-answer is present with its
    # description, summary line, and structured routing intents.
    assert "product-answer" in meta
    pa = meta["product-answer"]
    assert "Cognitive OS" in pa["description"] or "product" in pa["description"].lower()
    # Product-answer should not hardcode example utterances in SKILL.md;
    # semantic coverage comes from structured intent text plus the embedding model.
    assert isinstance(pa["routing_intents"], list)
    assert any("product_capability_question" in s for s in pa["routing_intents"])
    assert any("value_proposition_question" in s for s in pa["routing_intents"])


def test_loader_accepts_string_form_intents(tmp_path):
    """The loader must accept `routing_intents` items that are plain strings."""
    p = tmp_path / "demo" / "SKILL.md"
    p.parent.mkdir(parents=True)
    p.write_text(
        "<!-- SCOPE: both -->\n---\n"
        "name: demo\n"
        "description: Demo skill\n"
        "summary_line: A demo\n"
        "routing_intents:\n"
        "  - intent: foo\n"
        "    description: structured form\n"
        "  - plain string form\n"
        "---\n",
        encoding="utf-8",
    )
    meta = load_skill_metadata({"demo": p})
    intents = meta["demo"]["routing_intents"]
    assert "foo: structured form" in intents
    assert "plain string form" in intents


# ---------------------------------------------------------------------------
# Live semantic matching
# ---------------------------------------------------------------------------

PRODUCT_ANSWER_ACCEPTANCE_PROMPT = (
    "answer a Cognitive OS product positioning question from cached evidence cards"
)

# Held-out English eval set (precision target >= 0.8 over rows). Each row is
# (prompt, accept_set). Some skills overlap semantically, so we accept any
# skill in the listed set for known same-axis ambiguities.
HELD_OUT: list[tuple[str, tuple[str, ...]]] = [
    # /product-answer — capability / value-proposition questions
    (PRODUCT_ANSWER_ACCEPTANCE_PROMPT, ("product-answer",)),
    ("who is Cognitive OS for and what product value proposition should we tell buyers?", ("product-answer",)),
    ("can Cognitive OS help a developer team with product value and positioning?", ("product-answer",)),
    # /code-review — review-this-code framing.
    # optimize-skill SKILL.md also describes "review changed code for reuse,
    # quality, and efficiency" so it is an acceptable near-neighbour.
    ("review the changed code for quality and reuse issues", ("code-review", "optimize-skill")),
    ("review the changed code to detect problems", ("code-review", "optimize-skill")),
    ("code review focused on quality and reuse", ("code-review", "optimize-skill")),
    # /run-tests — execute tests in this repo
    ("run the tests in this repository", ("run-tests",)),
    ("execute repository tests", ("run-tests",)),
    # /repo-forensics — deep analysis of a git repository. repo-scout is
    # the same-axis sibling (lighter recon mode).
    ("perform deep forensic analysis of this git repository", ("repo-forensics", "repo-scout")),
    ("deep forensic analysis of this git repository", ("repo-forensics", "repo-scout")),
    # /security-audit — security review framing
    ("audit this codebase for security vulnerabilities", ("security-audit",)),
    ("audit this code for security vulnerabilities", ("security-audit",)),
]


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_product_positioning_question_routes_to_product_answer(matcher):
    """Product-positioning prompts must land on /product-answer.

    This proves product-answer routes from semantic intent text, not keyword
    regexes or example strings.
    """
    results = matcher.match(PRODUCT_ANSWER_ACCEPTANCE_PROMPT)
    assert results, "expected at least one semantic match"
    top = results[0]
    assert isinstance(top, SemanticMatch)
    assert top.skill_name == "product-answer", (
        f"top match was {top.skill_name} (conf={top.confidence:.3f}); "
        f"expected product-answer"
    )
    assert top.confidence > 0.6, (
        f"confidence {top.confidence:.3f} below acceptance bar 0.6"
    )
    assert top.invoke_command == "/product-answer"


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_semantic_precision_at_least_80pct(matcher):
    """Held-out semantic prompts must hit precision >= 0.8."""
    hits = 0
    misses = []
    for prompt, accept_set in HELD_OUT:
        results = matcher.match(prompt)
        actual = results[0].skill_name if results else None
        if actual in accept_set:
            hits += 1
        else:
            misses.append((prompt[:60], accept_set, actual))
    precision = hits / len(HELD_OUT)
    assert precision >= 0.8, (
        f"precision {precision:.2%} below 0.8 bar; misses: {misses}"
    )


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_cold_start_under_2s_with_cache(matcher):
    """Catalog encode + first query under 2 s once cache is warm.

    The cold-start guarantee in the ADR is < 2 s with disk cache; first
    ever boot pays the model download (one-off, not measured here).
    """
    # Warm the model and prime cache by running a query once.
    matcher.match("hello world")
    # Measure a *fresh* matcher that reads from disk cache.
    real = matcher  # type: ignore[assignment]
    fresh = SemanticSkillMatcher(
        indices=real._indices,
        cache_dir=real._cache_dir,
    )
    t0 = time.perf_counter()
    fresh.match("execute repository tests")
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"cold-start with cache took {elapsed:.2f}s"


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_warm_latency_under_100ms_p95(matcher):
    """Warm queries must average comfortably under 100 ms p95.

    100 calls over a short prompt; this is a smoke check, not a benchmark.
    """
    # Warm
    matcher.match("hello world")
    timings: list[float] = []
    prompts = [
        "execute repository tests",
        "review the code",
        "audit security",
        "what can this OS do for me",
        "agentic primitives",
    ]
    for i in range(100):
        t0 = time.perf_counter()
        matcher.match(prompts[i % len(prompts)])
        timings.append(time.perf_counter() - t0)
    timings.sort()
    p95 = timings[int(0.95 * len(timings)) - 1]
    assert p95 < 0.1, f"warm p95 {p95*1000:.1f}ms exceeded 100ms"


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_skill_drift_invalidates_cache(tmp_path):
    """Changing a SKILL.md description bumps the catalog signature.

    The cache file is keyed by sha(model, names, corpus lines). Mutating
    the corpus produces a different filename — old cache untouched, new
    one written.
    """
    from lib.semantic_skill_matcher import _SkillIndex, _catalog_signature

    idx_a = _SkillIndex(
        skill_name="demo",
        invoke_command="/demo",
        description="describe one thing",
    )
    idx_b = _SkillIndex(
        skill_name="demo",
        invoke_command="/demo",
        description="describe something completely different now",
    )
    sig_a = _catalog_signature([idx_a], sm.DEFAULT_MODEL_NAME)
    sig_b = _catalog_signature([idx_b], sm.DEFAULT_MODEL_NAME)
    assert sig_a != sig_b, "signature must change when SKILL.md description changes"


# ----------------------------------------------------------------------------
# Regression gate: cos-language-dependence-audit baseline
# ----------------------------------------------------------------------------
# Pre-ADR-296 baseline (captured 2026-05-13 with --min-severity low):
#   total_findings = 326, medium_severity = 97, primitives_affected = 112
# This test asserts the audit count does not grow. ADR-296 makes most of
# these obsolete because the semantic matcher reads SKILL.md description
# directly, so routing_patterns can be removed over time. Allowing the
# count to grow would silently re-introduce the monolingual-regex anti-
# pattern. Cap is set above the 2026-05-13 baseline with a small headroom
# for new skills that haven't yet been migrated.

@pytest.mark.audit
def test_language_dependence_audit_does_not_regress():
    """ADR-296 regression gate.

    Runs scripts/cos-language-dependence-audit and asserts the total
    finding count stays at or below the captured baseline. New skills
    landing patterns will tick this up; the cap forces the contributor
    to either justify the regex (and bump the cap explicitly) or use the
    semantic path instead.
    """
    import json
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "cos-language-dependence-audit"
    if not script.exists():
        pytest.skip("language-dependence-audit script not present")

    proc = subprocess.run(
        [str(script), "--json", "--min-severity", "medium"],
        capture_output=True,
        text=True,
        cwd=str(repo),
        timeout=60,
    )
    _ = sys  # quiet F401 — module retained for future env injection if needed
    assert proc.returncode == 0, f"audit failed: {proc.stderr[:400]}"
    data = json.loads(proc.stdout)
    actionable = int(data.get("finding_count") or 0)

    # ADR-302 made low-severity compatibility regexes inventory, not blocking debt.
    # This regression gate therefore caps actionable medium/high findings only.
    CAP = 0
    assert actionable <= CAP, (
        f"cos-language-dependence-audit regressed: {actionable} actionable findings "
        f"(cap {CAP}). Prefer ADR-296 semantic routing or add routing_intents/"
        f"summary_line evidence before adding natural-language regexes."
    )
