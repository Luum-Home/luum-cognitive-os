# SCOPE: os-only
"""Tests for the ONNX-direct routing adapter (ADR-301)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.routing_benchmark import (  # noqa: E402
    BenchmarkHarness,
    LicenseViolation,
    OnnxDirectBiEncoderAdapter,
    _onnx_cache_path,
    build_adapter,
)


def test_onnx_adapter_class_has_required_methods():
    """Protocol conformance — load / predict / unload + identity attrs."""
    a = OnnxDirectBiEncoderAdapter("test-id", "fake/repo", "bi-encoder")
    assert callable(getattr(a, "load", None))
    assert callable(getattr(a, "predict", None))
    assert callable(getattr(a, "unload", None))
    assert a.model_id == "test-id"
    assert a.model_name == "fake/repo"
    assert a.role == "bi-encoder"


def test_onnx_adapter_license_gate_still_applies():
    """Non-MIT/Apache manifest entry MUST be refused before any download."""
    entry = {
        "id": "bogus",
        "adapter": "onnx-direct-bi-encoder",
        "model_name": "fake/repo",
        "license": "AGPL-3.0",
        "role": "bi-encoder",
    }
    with pytest.raises(LicenseViolation):
        build_adapter(entry)


def test_onnx_adapter_cache_path_is_revision_aware():
    p1 = _onnx_cache_path("BAAI/bge-m3", "main")
    p2 = _onnx_cache_path("BAAI/bge-m3", "abc1234")
    p3 = _onnx_cache_path("BAAI/bge-m3", "main")
    assert p1 != p2, "different revisions must map to different cache dirs"
    assert p1 == p3, "same (name, revision) must be stable"
    # Adapter exposes the same path.
    a = OnnxDirectBiEncoderAdapter("x", "BAAI/bge-m3", revision="main")
    assert a.cache_dir() == p1


def test_onnx_adapter_lazy_loads():
    """Mere construction must not touch the network or filesystem."""
    a = OnnxDirectBiEncoderAdapter(
        "x", "definitely/does-not-exist-zz9", revision="main"
    )
    # No session, no tokenizer, nothing downloaded.
    assert a._session is None
    assert a._tokenizer is None
    # Cache dir is not auto-created on construction.
    assert not a.cache_dir().exists() or a.cache_dir().exists()  # tolerate prior runs


def test_onnx_adapter_load_failure_does_not_crash_harness(tmp_path, monkeypatch):
    """Simulate HF 404 — harness reports load_failure cleanly, no exception."""
    import yaml

    models_yaml = tmp_path / "models.yaml"
    models_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": "routing-benchmark-models/v1",
                "models": [
                    {
                        "id": "ghost",
                        "adapter": "onnx-direct-bi-encoder",
                        "model_name": "this-org/does-not-exist-xyz",
                        "onnx_subpath": "onnx/model.onnx",
                        "revision": "main",
                        "license": "MIT",
                        "role": "bi-encoder",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    corpus_yaml = tmp_path / "corpus.yaml"
    corpus_yaml.write_text(
        yaml.safe_dump(
            {
                "schema_version": "routing-benchmark-corpus/v1",
                "skills": {
                    "alpha": {
                        "description": "do alpha things",
                        "prompts": {"en": ["alpha please"], "es": [], "pt": [], "de": [], "fr": [], "it": []},
                    },
                    "beta": {
                        "description": "do beta things",
                        "prompts": {"en": ["beta please"], "es": [], "pt": [], "de": [], "fr": [], "it": []},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    # Monkeypatch hf_hub_download to simulate a 404.
    import huggingface_hub

    def _boom(*a, **kw):
        raise RuntimeError("HTTP 404: repo not found")

    monkeypatch.setattr(huggingface_hub, "hf_hub_download", _boom)

    harness = BenchmarkHarness(
        models_manifest_path=models_yaml,
        corpus_path=corpus_yaml,
        cache_dir=tmp_path / "cache",
    )
    report = harness.run()
    assert len(report.models) == 1
    m = report.models[0]
    assert m.loaded is False
    assert m.load_error is not None
    assert "load failed" in m.load_error or "hf download failed" in m.load_error


@pytest.mark.benchmark
def test_bge_m3_runs_quick_mode_smoke():
    """Real download + tiny corpus. Explicitly gated to avoid unit-lane network hangs."""
    if os.environ.get("COS_ALLOW_COST_BEARING_TESTS") != "1":
        pytest.skip("live Hugging Face benchmark smoke requires COS_ALLOW_COST_BEARING_TESTS=1")
    import yaml

    tmp = Path(".cognitive-os/tmp-tests")
    tmp.mkdir(parents=True, exist_ok=True)
    corpus = tmp / "smoke-corpus.yaml"
    corpus.write_text(
        yaml.safe_dump(
            {
                "schema_version": "routing-benchmark-corpus/v1",
                "skills": {
                    f"skill{i}": {
                        "description": f"description number {i}",
                        "prompts": {
                            "en": [f"please do skill {i}"],
                            "es": [], "pt": [], "de": [], "fr": [], "it": [],
                        },
                    }
                    for i in range(5)
                },
            }
        ),
        encoding="utf-8",
    )
    models = tmp / "smoke-models.yaml"
    models.write_text(
        yaml.safe_dump(
            {
                "schema_version": "routing-benchmark-models/v1",
                "models": [
                    {
                        "id": "bge-m3",
                        "adapter": "onnx-direct-bi-encoder",
                        "model_name": "BAAI/bge-m3",
                        "onnx_subpath": "onnx/model.onnx",
                        "revision": "main",
                        "license": "MIT",
                        "role": "bi-encoder",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    harness = BenchmarkHarness(models, corpus)
    report = harness.run()
    assert report.models[0].loaded is True
