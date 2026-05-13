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
    # description + (after ADR-296) string-form multilingual utterances.
    assert "product-answer" in meta
    pa = meta["product-answer"]
    assert "Cognitive OS" in pa["description"] or "product" in pa["description"].lower()
    # routing_intents may be a mix of struct dicts (rendered as
    # "intent: description") and plain strings — both forms must parse.
    assert isinstance(pa["routing_intents"], list)
    assert any("¿puede" in s or "puede ayudar" in s for s in pa["routing_intents"]), (
        "ADR-296 added multilingual example utterances to product-answer"
    )


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
# Live multilingual matching
# ---------------------------------------------------------------------------

# The Spanish capability-question that motivated ADR-296.
SPANISH_ACCEPTANCE_PROMPT = (
    "Si yo soy un dev que tengo limitaciones en cuanto al conocimiento de las "
    "buenas prácticas, codigo y arquitectura limpia, seguridad, construcción "
    "de tests, documentación, primitivas de agentes, entre otras cosas, este "
    "SO me puede ayudar?"
)

# Held-out multilingual eval set (precision target ≥ 0.8 over rows). Each
# row is (prompt, expected_skill). Some skills overlap semantically so we
# accept any of `expected_skill` (str or tuple).
# Each row: (prompt, accept_set). The `code-review` / `optimize-skill`
# axis has genuine catalog ambiguity — both skills review code — so we
# treat either as a hit for "review my code" prompts. Same logic for
# `repo-forensics` vs `repo-scout`.
HELD_OUT: list[tuple[str, tuple[str, ...]]] = [
    # /product-answer — capability / value-proposition questions
    (SPANISH_ACCEPTANCE_PROMPT, ("product-answer",)),
    ("Can this OS help a developer who does not know best practices?", ("product-answer",)),
    ("¿puede ayudarme este SO como desarrollador?", ("product-answer",)),
    ("Este SO serve para um desenvolvedor sem experiência?", ("product-answer",)),
    ("Ist dieses System für einen Entwickler ohne Architekturkenntnisse nützlich?", ("product-answer",)),
    ("Est-ce que ce SO peut aider un développeur sans expérience?", ("product-answer",)),
    ("Può aiutare uno sviluppatore senza esperienza in architettura?", ("product-answer",)),
    # /code-review — review-this-code framing across languages.
    # optimize-skill SKILL.md also describes "review changed code for reuse,
    # quality, and efficiency" so it is an acceptable near-neighbour.
    ("review the changed code for quality and reuse issues", ("code-review", "optimize-skill")),
    ("revisar el código cambiado para detectar problemas", ("code-review", "optimize-skill")),
    ("revisão de código com foco em qualidade e reutilização", ("code-review", "optimize-skill")),
    # /run-tests — execute tests in this repo
    ("run the tests in this repository", ("run-tests",)),
    ("ejecutar los tests de este repositorio", ("run-tests",)),
    ("execute os testes deste repositório", ("run-tests",)),
    # /repo-forensics — deep analysis of a git repository. repo-scout is
    # the same-axis sibling (lighter recon mode).
    ("perform deep forensic analysis of this git repository", ("repo-forensics", "repo-scout")),
    ("análisis forense profundo de este repositorio git", ("repo-forensics", "repo-scout")),
    # /security-audit — security review framing
    ("audit this codebase for security vulnerabilities", ("security-audit",)),
    ("auditar este código en busca de vulnerabilidades de seguridad", ("security-audit",)),
]


@live
@pytest.mark.skipif(not FASTEMBED_AVAILABLE, reason="fastembed not installed")
def test_spanish_capability_question_routes_to_product_answer(matcher):
    """The exact operator-screenshot prompt MUST land on /product-answer ≥ 0.6.

    This is the ADR-296 acceptance test, copied verbatim from the spec.
    """
    results = matcher.match(SPANISH_ACCEPTANCE_PROMPT)
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
def test_multilingual_precision_at_least_80pct(matcher):
    """Held-out prompts in 6 languages must hit precision ≥ 0.8."""
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
    fresh.match("ejecutar los tests")
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
        "ejecutar los tests",
        "review the code",
        "auditar seguridad",
        "what can this OS do for me",
        "primitivas de agentes",
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
