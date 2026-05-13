# SCOPE: os-only
"""Unit tests for ADR-298 routing-benchmark harness."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from lib import routing_benchmark as rb
from lib.routing_benchmark import (
    BenchmarkHarness,
    LicenseViolation,
    RoutingAdapter,
    enforce_license_gate,
    license_is_permitted,
    load_corpus,
    load_models_manifest,
    write_report_json,
    write_report_markdown,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


VALID_MODELS_YAML = textwrap.dedent(
    """\
    schema_version: routing-benchmark-models/v1
    models:
      - id: baseline
        adapter: stub
        model_name: stub/baseline
        license: Apache-2.0
        role: bi-encoder
      - id: alternate
        adapter: stub
        model_name: stub/alternate
        license: MIT
        role: bi-encoder
    """
)

VALID_CORPUS_YAML = textwrap.dedent(
    """\
    schema_version: routing-benchmark-corpus/v1
    skills:
      product-answer:
        description: "Answer product questions from cached cards."
        prompts:
          en: ["what is our differentiator"]
          es: ["¿cuál es nuestro diferenciador?"]
          pt: ["qual é o nosso diferenciador?"]
          de: ["was ist unser Differenzierungsmerkmal?"]
          fr: ["quel est notre facteur différenciant?"]
          it: ["qual è il nostro differenziatore?"]
      security-audit:
        description: "Run a security audit of recent changes."
        prompts:
          en: ["run a security audit"]
          es: ["haz una auditoría de seguridad"]
          pt: ["faça uma auditoria de segurança"]
          de: ["führe ein Security-Audit aus"]
          fr: ["fais un audit de sécurité"]
          it: ["esegui un audit di sicurezza"]
    """
)


@pytest.fixture
def models_path(tmp_path: Path) -> Path:
    p = tmp_path / "models.yaml"
    p.write_text(VALID_MODELS_YAML, encoding="utf-8")
    return p


@pytest.fixture
def corpus_path(tmp_path: Path) -> Path:
    p = tmp_path / "corpus.yaml"
    p.write_text(VALID_CORPUS_YAML, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Stub adapter — deterministic, no network
# ---------------------------------------------------------------------------


class _StubAdapter:
    """Returns top match = first candidate whose name appears (lowercased)
    in the prompt; otherwise first candidate. Score = 1.0 / (rank + 1)."""

    def __init__(self, model_id: str, model_name: str, role: str = "bi-encoder"):
        self.model_id = model_id
        self.model_name = model_name
        self.role = role
        self._loaded = False

    def load(self) -> None:
        self._loaded = True

    def predict(
        self, prompt: str, candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        assert self._loaded, "load() must be called first"
        plow = prompt.lower()
        # Tokenise skill name to single words for matching.
        ranked: List[Tuple[str, float]] = []
        for i, (name, _desc) in enumerate(candidates):
            score = 0.0
            tokens = name.replace("-", " ").split()
            for t in tokens:
                if t.lower() in plow:
                    score += 1.0
            ranked.append((name, score))
        ranked.sort(key=lambda kv: kv[1], reverse=True)
        return ranked

    def unload(self) -> None:
        self._loaded = False


def _stub_factory(entry: Dict[str, Any]) -> _StubAdapter:
    enforce_license_gate(entry)
    return _StubAdapter(entry["id"], entry["model_name"], entry.get("role", ""))


# ---------------------------------------------------------------------------
# License gate
# ---------------------------------------------------------------------------


def test_license_gate_accepts_permitted():
    for lic in ("MIT", "Apache-2.0", "BSD-3-Clause", "apache", "bsd"):
        assert license_is_permitted(lic)


def test_license_gate_rejects_non_permitted():
    for lic in ("AGPL-3.0", "CC-BY-NC", "SSPL", "BSL-1.1", None, ""):
        assert not license_is_permitted(lic)


def test_license_gate_blocks_unknown_license(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent(
            """\
            schema_version: routing-benchmark-models/v1
            models:
              - id: nope
                adapter: stub
                model_name: x/y
                license: CC-BY-NC
                role: bi-encoder
            """
        ),
        encoding="utf-8",
    )
    manifest = load_models_manifest(bad)
    with pytest.raises(LicenseViolation):
        enforce_license_gate(manifest[0])


def test_models_manifest_license_gate_under_strict(
    models_path: Path, corpus_path: Path, tmp_path: Path
):
    # Replace one entry with a forbidden license.
    bad = tmp_path / "bad-models.yaml"
    bad.write_text(
        VALID_MODELS_YAML.replace("Apache-2.0", "AGPL-3.0"), encoding="utf-8"
    )
    harness = BenchmarkHarness(
        models_manifest_path=bad,
        corpus_path=corpus_path,
        adapter_factory=_stub_factory,
        warm_queries=5,
    )
    with pytest.raises(LicenseViolation):
        harness.run(strict=True)


# ---------------------------------------------------------------------------
# Corpus / manifest loaders
# ---------------------------------------------------------------------------


def test_corpus_loader_parses_seed(corpus_path: Path):
    corpus = load_corpus(corpus_path)
    assert set(corpus.keys()) == {"product-answer", "security-audit"}
    pa = corpus["product-answer"]
    assert pa["description"].startswith("Answer product")
    for lang in ("en", "es", "pt", "de", "fr", "it"):
        assert pa["prompts"][lang], f"missing prompts for {lang}"


def test_corpus_loader_rejects_wrong_schema(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("schema_version: wrong/v9\nskills: {}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_corpus(p)


def test_models_manifest_rejects_duplicate_ids(tmp_path: Path):
    p = tmp_path / "dup.yaml"
    p.write_text(
        textwrap.dedent(
            """\
            schema_version: routing-benchmark-models/v1
            models:
              - id: x
                adapter: stub
                model_name: a/b
                license: MIT
                role: bi-encoder
              - id: x
                adapter: stub
                model_name: a/c
                license: MIT
                role: bi-encoder
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_models_manifest(p)


# ---------------------------------------------------------------------------
# Adapter protocol conformance
# ---------------------------------------------------------------------------


def test_adapter_protocol_stub_conforms():
    adapter: RoutingAdapter = _StubAdapter("stub", "x/y")
    adapter.load()
    out = adapter.predict("product answer", [("product-answer", "desc"), ("other", "x")])
    assert out[0][0] == "product-answer"
    adapter.unload()


def test_adapter_protocol_fastembed_class_has_required_methods():
    # We don't load weights here — just verify the class satisfies the
    # protocol via duck typing (load/predict/unload + attrs).
    inst = rb.FastembedBiEncoderAdapter("baseline", "stub/baseline")
    for attr in ("model_id", "model_name", "role"):
        assert hasattr(inst, attr), f"missing {attr}"
    for meth in ("load", "predict", "unload"):
        assert callable(getattr(inst, meth))


# ---------------------------------------------------------------------------
# End-to-end with stub adapter (no model download)
# ---------------------------------------------------------------------------


def test_benchmark_runs_with_stub_factory(models_path: Path, corpus_path: Path):
    harness = BenchmarkHarness(
        models_manifest_path=models_path,
        corpus_path=corpus_path,
        adapter_factory=_stub_factory,
        warm_queries=5,
    )
    report = harness.run()
    assert len(report.models) == 2
    for m in report.models:
        assert m.loaded
        # Stub picks the skill whose name token appears in the prompt;
        # for "security-audit" + "audit" prompts that's a clean hit;
        # for "product-answer" most prompts don't contain those tokens
        # literally, but every query gets ranked.
        assert m.total_queries > 0
        assert 0.0 <= m.precision_at_1 <= 1.0
        assert m.warm_p95_ms >= 0
        assert m.license_ok
        assert m.load_error is None
        # 6 languages should all be represented.
        assert {pl.language for pl in m.per_language} == set(rb.LANGUAGES)


def test_benchmark_idempotent_via_cache(
    models_path: Path, corpus_path: Path, tmp_path: Path
):
    cache = tmp_path / "cache"
    harness1 = BenchmarkHarness(
        models_manifest_path=models_path,
        corpus_path=corpus_path,
        adapter_factory=_stub_factory,
        warm_queries=5,
        cache_dir=cache,
    )
    r1 = harness1.run()
    # Second run with a factory that would crash if invoked — proves cache hit.
    def _exploding_factory(_entry: Dict[str, Any]) -> RoutingAdapter:
        raise AssertionError("factory should not be called on cache hit")

    harness2 = BenchmarkHarness(
        models_manifest_path=models_path,
        corpus_path=corpus_path,
        adapter_factory=_exploding_factory,
        warm_queries=5,
        cache_dir=cache,
    )
    r2 = harness2.run()
    assert r1.corpus_signature == r2.corpus_signature
    for m1, m2 in zip(r1.models, r2.models):
        assert m1.precision_at_1 == m2.precision_at_1
        assert m1.model_id == m2.model_id


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def test_report_writer_produces_markdown_and_json(
    models_path: Path, corpus_path: Path, tmp_path: Path
):
    harness = BenchmarkHarness(
        models_manifest_path=models_path,
        corpus_path=corpus_path,
        adapter_factory=_stub_factory,
        warm_queries=5,
        cache_dir=tmp_path / "cache",
    )
    report = harness.run()
    md = tmp_path / "report.md"
    js = tmp_path / "report.json"
    write_report_markdown(report, md)
    write_report_json(report, js)

    md_text = md.read_text(encoding="utf-8")
    assert "Routing Model Benchmark Report" in md_text
    assert "precision@1" in md_text
    assert "Per-Language Precision@1" in md_text
    assert "Recommendation Block" in md_text

    parsed = json.loads(js.read_text(encoding="utf-8"))
    assert parsed["schema_version"] == rb.REPORT_SCHEMA_VERSION
    assert parsed["corpus_skills"] == 2
    assert len(parsed["models"]) == 2
    for m in parsed["models"]:
        assert "per_language" in m
        assert "warm_p95_ms" in m


# ---------------------------------------------------------------------------
# Real-model live test (skippable)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_baseline_minilm_runs_quick_mode(tmp_path: Path):
    """Live integration: actually invoke the production fastembed model.

    Skip with `pytest -m 'not benchmark'`. This test downloads ~220MB
    of weights on first run and is slow.
    """
    try:
        import fastembed  # noqa: F401
    except Exception:
        pytest.skip("fastembed not installed")

    models = tmp_path / "models.yaml"
    models.write_text(
        textwrap.dedent(
            """\
            schema_version: routing-benchmark-models/v1
            models:
              - id: baseline-minilm
                adapter: fastembed-bi-encoder
                model_name: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
                license: Apache-2.0
                role: bi-encoder
            """
        ),
        encoding="utf-8",
    )
    corpus = Path("manifests/routing-benchmark-corpus.yaml")
    if not corpus.exists():
        pytest.skip("seed corpus missing — run from repo root")

    harness = BenchmarkHarness(
        models_manifest_path=models,
        corpus_path=corpus,
        warm_queries=10,
        cache_dir=tmp_path / "cache",
    )
    report = harness.run(quick=True)
    assert len(report.models) == 1
    m = report.models[0]
    assert m.loaded, f"baseline-minilm should load: {m.load_error}"
    assert m.total_queries > 0
    out_dir = tmp_path / "out"
    write_report_markdown(report, out_dir / "r.md")
    write_report_json(report, out_dir / "r.json")
    assert (out_dir / "r.md").exists()
    assert (out_dir / "r.json").exists()
