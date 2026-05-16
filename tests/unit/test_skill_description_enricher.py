# SCOPE: os-only
"""Unit tests for ADR-299 skill-description enrichment.

Tests are mocked at the dispatch boundary — no live LLM calls. The
``@pytest.mark.enrichment`` mark gates the live-LLM oracle test
(``test_enriched_corpus_improves_baseline_routing``) so CI runs unmarked
tests deterministically:

    pytest tests/unit/test_skill_description_enricher.py -v -m "not enrichment"
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Callable

import pytest

from lib.skill_description_enricher import (
    AUDIT_REL,
    enrich_skills,
    parse_llm_response,
    utterances_to_intent_entries,
)

pytestmark = []  # individual tests opt-in to @pytest.mark.enrichment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_skill(tmp_path: Path, name: str, *, frontmatter_extra: str = "") -> Path:
    """Create a minimal SKILL.md under ``tmp_path/skills/<name>/SKILL.md``."""
    sdir = tmp_path / "skills" / name
    sdir.mkdir(parents=True, exist_ok=True)
    fm = (
        "---\n"
        f"name: {name}\n"
        f"description: Test skill {name} used by enricher unit tests.\n"
        "version: 1.0.0\n"
        f"invoke_command: /{name}\n"
        f"{frontmatter_extra}"
        "---\n\n"
        f"# {name}\n\nBody content.\n"
    )
    path = sdir / "SKILL.md"
    path.write_text(fm, encoding="utf-8")
    return path


def _ok_response(langs, n_per_lang: int) -> dict[str, Any]:
    """Build a synthetic LLM response with exactly ``n_per_lang`` utterances."""
    payload = {
        lang: [f"utterance {lang} #{i}" for i in range(1, n_per_lang + 1)]
        for lang in langs
    }
    return {
        "success": True,
        "text": json.dumps(payload),
        "cost_usd": 0.0005,
        "provider_used": "alibaba_qwen",
        "latency_ms": 42,
        "error": "",
    }


def _make_dispatch(langs, n_per_lang: int) -> Callable[[str], dict[str, Any]]:
    def _fn(_prompt: str) -> dict[str, Any]:
        return _ok_response(langs, n_per_lang)

    return _fn


# ---------------------------------------------------------------------------
# 1. Returns intents per language
# ---------------------------------------------------------------------------


def test_enricher_returns_intents_per_language(tmp_path: Path) -> None:
    _write_skill(tmp_path, "alpha")
    langs = ["en", "es"]
    report = enrich_skills(
        tmp_path,
        skills=["alpha"],
        languages=langs,
        intents_per_lang=2,
        dispatch_fn=_make_dispatch(langs, 2),
        rate_limit_per_minute=0,
    )
    assert report.skills_written == 1
    written = (tmp_path / "skills" / "alpha" / "SKILL.md").read_text(encoding="utf-8")
    assert "auto_generated: true" in written
    # 2 utterances * 2 languages = 4 auto entries
    assert written.count("auto_generated: true") == 4
    assert "language: en" in written
    assert "language: es" in written


# ---------------------------------------------------------------------------
# 2. Preserves human-curated intents
# ---------------------------------------------------------------------------


def test_preserves_human_curated_intents(tmp_path: Path) -> None:
    extra = textwrap.dedent(
        """\
        routing_intents:
        - intent: human_curated
          description: This was hand-written by an operator and must survive.
          confidence: 0.95
        """
    )
    path = _write_skill(tmp_path, "beta", frontmatter_extra=extra)
    langs = ["en"]
    enrich_skills(
        tmp_path,
        skills=["beta"],
        languages=langs,
        intents_per_lang=1,
        dispatch_fn=_make_dispatch(langs, 1),
        rate_limit_per_minute=0,
    )
    after = path.read_text(encoding="utf-8")
    assert "human_curated" in after
    assert "This was hand-written by an operator" in after
    # And new auto entry is appended after it
    assert "auto_generated: true" in after


# ---------------------------------------------------------------------------
# 3. Auto-generated marker → idempotency, --force overrides
# ---------------------------------------------------------------------------


def test_auto_generated_marker_allows_overwrite_with_force(tmp_path: Path) -> None:
    extra = textwrap.dedent(
        """\
        routing_intents:
        - intent: auto_existing
          description: previously generated utterance
          confidence: 0.85
          language: en
          auto_generated: true
        """
    )
    path = _write_skill(tmp_path, "gamma", frontmatter_extra=extra)
    langs = ["en"]

    # Run 1 — without --force: no rewrite (already enriched).
    report = enrich_skills(
        tmp_path,
        skills=["gamma"],
        languages=langs,
        intents_per_lang=1,
        dispatch_fn=_make_dispatch(langs, 1),
        force=False,
        rate_limit_per_minute=0,
    )
    assert report.skills_written == 0
    assert any(r.skipped_reason == "already_enriched" for r in report.results)

    # Run 2 — with --force: rewrite.
    report = enrich_skills(
        tmp_path,
        skills=["gamma"],
        languages=langs,
        intents_per_lang=1,
        dispatch_fn=_make_dispatch(langs, 1),
        force=True,
        rate_limit_per_minute=0,
    )
    assert report.skills_written == 1
    text = path.read_text(encoding="utf-8")
    assert "auto_generated: true" in text


# ---------------------------------------------------------------------------
# 4. Strict-JSON guard
# ---------------------------------------------------------------------------


def test_strict_json_parse_rejects_bad_response(tmp_path: Path) -> None:
    path = _write_skill(tmp_path, "delta")
    original = path.read_text(encoding="utf-8")

    def _bad(_prompt: str) -> dict[str, Any]:
        return {
            "success": True,
            "text": "Sure! Here are some utterances:\n- foo\n- bar",
            "cost_usd": 0.0005,
            "provider_used": "alibaba_qwen",
        }

    report = enrich_skills(
        tmp_path,
        skills=["delta"],
        languages=["en"],
        intents_per_lang=2,
        dispatch_fn=_bad,
        rate_limit_per_minute=0,
    )
    assert report.skills_written == 0
    assert any(r.skipped_reason == "invalid_llm_response" for r in report.results)
    # File is untouched
    assert path.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# 5. Cost cap halts batch
# ---------------------------------------------------------------------------


def test_cost_cap_halts_enrichment(tmp_path: Path) -> None:
    for n in ("s1", "s2", "s3", "s4"):
        _write_skill(tmp_path, n)
    langs = ["en"]

    def _expensive(_prompt: str) -> dict[str, Any]:
        return {
            "success": True,
            "text": json.dumps({"en": ["u1", "u2"]}),
            "cost_usd": 0.50,
            "provider_used": "test",
        }

    report = enrich_skills(
        tmp_path,
        skills=None,  # all → 4 skills
        languages=langs,
        intents_per_lang=2,
        dispatch_fn=_expensive,
        cost_cap_usd=1.0,  # 2 calls × $0.50 → trips after second
        rate_limit_per_minute=0,
    )
    assert report.halted_by_cost_cap is True
    # Halted, but partial save: at least 1 file was written.
    assert report.skills_written >= 1
    assert report.skills_processed <= 4


# ---------------------------------------------------------------------------
# 6. Kill switch
# ---------------------------------------------------------------------------


def test_kill_switch_short_circuits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_skill(tmp_path, "epsilon")
    monkeypatch.setenv("COS_DISABLE_ENRICHMENT", "1")
    called = {"n": 0}

    def _spy(_prompt: str) -> dict[str, Any]:
        called["n"] += 1
        return _ok_response(["en"], 1)

    report = enrich_skills(
        tmp_path,
        skills=["epsilon"],
        languages=["en"],
        intents_per_lang=1,
        dispatch_fn=_spy,
        rate_limit_per_minute=0,
    )
    assert report.kill_switch_active is True
    assert report.skills_processed == 0
    assert called["n"] == 0


# ---------------------------------------------------------------------------
# 7. Dry-run writes nothing
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    path = _write_skill(tmp_path, "zeta")
    mtime_before = path.stat().st_mtime_ns
    original = path.read_text(encoding="utf-8")

    report = enrich_skills(
        tmp_path,
        skills=["zeta"],
        languages=["en"],
        intents_per_lang=1,
        dispatch_fn=_make_dispatch(["en"], 1),
        dry_run=True,
        rate_limit_per_minute=0,
    )
    assert report.dry_run is True
    assert report.skills_written == 0
    # Proposal still computed
    assert any(r.intents_added > 0 for r in report.results)
    # File mtime + bytes unchanged
    assert path.stat().st_mtime_ns == mtime_before
    assert path.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# 8. Audit trail
# ---------------------------------------------------------------------------


def test_audit_trail_emits_one_line_per_call(tmp_path: Path) -> None:
    for n in ("a1", "a2", "a3"):
        _write_skill(tmp_path, n)
    langs = ["en"]
    enrich_skills(
        tmp_path,
        skills=["a1", "a2", "a3"],
        languages=langs,
        intents_per_lang=1,
        dispatch_fn=_make_dispatch(langs, 1),
        rate_limit_per_minute=0,
    )
    audit = tmp_path / AUDIT_REL
    assert audit.exists()
    lines = [ln for ln in audit.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        rec = json.loads(ln)
        assert rec["success"] is True
        assert rec["skill"] in {"a1", "a2", "a3"}
        assert rec["languages"] == langs


# ---------------------------------------------------------------------------
# 9. Validation hook — enriched corpus improves baseline routing
# ---------------------------------------------------------------------------


@pytest.mark.enrichment
def test_enriched_corpus_improves_baseline_routing(tmp_path: Path) -> None:
    """Architecture proof: enriching a description-only catalog with multilingual
    utterances raises the semantic matcher's accuracy on language-shifted prompts.

    Mocked dispatch is sufficient to prove the *architecture* — we don't need a
    real LLM to show the enricher writes intents the matcher then picks up.
    """
    pytest.importorskip("fastembed")
    pytest.importorskip("numpy")

    from lib.semantic_skill_matcher import (
        SemanticSkillMatcher,
        _SkillIndex,
    )

    skills_and_intents = {
        "deploy-checker": {
            "desc": "Verify deployment readiness before pushing to production.",
            "es": [
                "puedo verificar si esta listo el deploy a produccion",
                "como compruebo que el despliegue esta listo",
            ],
        },
        "log-analyzer": {
            "desc": "Analyze application logs to find errors and warnings.",
            "es": [
                "analizar los logs de la aplicacion para encontrar errores",
                "revisar los registros de la app",
            ],
        },
        "schema-migrate": {
            "desc": "Run database schema migrations safely with rollback.",
            "es": [
                "migrar el esquema de la base de datos",
                "ejecutar migraciones de base de datos con rollback",
            ],
        },
        "perf-profile": {
            "desc": "Profile application performance and find bottlenecks.",
            "es": [
                "perfilar el rendimiento de la aplicacion",
                "encontrar cuellos de botella de rendimiento",
            ],
        },
        "secret-scan": {
            "desc": "Scan repository for leaked credentials and secrets.",
            "es": [
                "escanear el repo en busca de credenciales filtradas",
                "buscar secretos expuestos en el codigo",
            ],
        },
    }

    def _build_matcher(with_intents: bool) -> SemanticSkillMatcher:
        indices = []
        for name, payload in skills_and_intents.items():
            intents = list(payload["es"]) if with_intents else []
            indices.append(
                _SkillIndex(
                    skill_name=name,
                    invoke_command=f"/{name}",
                    description=payload["desc"],
                    summary_line="",
                    routing_intents=intents,
                )
            )
        return SemanticSkillMatcher(indices, cache_dir=tmp_path / f"cache-{with_intents}")

    # Spanish prompts — one per skill, paraphrased.
    test_prompts = {
        "deploy-checker": "como verifico si esta listo el despliegue a prod",
        "log-analyzer": "I need to analyze logs to find failures",
        "schema-migrate": "quiero correr migraciones de la base de datos",
        "perf-profile": "ayuda con cuellos de botella de rendimiento",
        "secret-scan": "buscar secretos filtrados en el repositorio",
    }

    def _accuracy(matcher: SemanticSkillMatcher) -> float:
        hits = 0
        for expected, prompt in test_prompts.items():
            results = matcher.match(prompt, threshold=0.30)
            if results and results[0].skill_name == expected:
                hits += 1
        return hits / len(test_prompts)

    baseline_acc = _accuracy(_build_matcher(with_intents=False))
    enriched_acc = _accuracy(_build_matcher(with_intents=True))

    # Strict ADR-299 hypothesis: enrichment lifts (or at least matches) baseline.
    # Inequality must be strict if baseline < 1.0 — if baseline is already
    # perfect there's no headroom to lift, which is still a pass.
    if baseline_acc < 1.0:
        assert enriched_acc > baseline_acc, (
            f"Enrichment did not improve routing: "
            f"baseline={baseline_acc}, enriched={enriched_acc}"
        )
    else:
        assert enriched_acc >= baseline_acc


# ---------------------------------------------------------------------------
# Small parsing units
# ---------------------------------------------------------------------------


def test_parse_llm_response_handles_fenced_json() -> None:
    text = "```json\n" + json.dumps({"en": ["a", "b"], "es": ["c", "d"]}) + "\n```"
    out = parse_llm_response(text, ["en", "es"], 2)
    assert out == {"en": ["a", "b"], "es": ["c", "d"]}


def test_parse_llm_response_rejects_underproduced() -> None:
    text = json.dumps({"en": ["only one"]})
    out = parse_llm_response(text, ["en"], 2)
    assert out is None


def test_utterances_flatten_with_marker() -> None:
    entries = utterances_to_intent_entries({"en": ["a", "b"]}, skill_name="x")
    assert len(entries) == 2
    for e in entries:
        assert e["auto_generated"] is True
        assert e["language"] == "en"
        assert e["intent"].startswith("auto_x_en_")
