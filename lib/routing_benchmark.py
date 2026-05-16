# SCOPE: os-only
"""Reproducible model-evaluation harness for the COS skill router (ADR-298).

The COS skill router (`lib/skill_router.py`) routes English user prompts to one
of ~385 skills. Two recent ADRs introduced model-driven layers:

* ADR-296 — bi-encoder semantic matcher (FastEmbed + MiniLM)
* ADR-297 — LLM tie-breaker for ambiguous regex/embedding results

This harness is the artifact that backs every future model-selection ADR.
Any candidate routing model (bi-encoder, cross-encoder reranker, LLM)
MUST be evaluated via :class:`BenchmarkHarness` before adoption. The
benchmark report (Markdown + JSON) is the evidence those ADRs cite.

Key properties
--------------
* **License gate first.** Any model whose declared license is not one of
  {MIT, BSD, BSD-2-Clause, BSD-3-Clause, Apache, Apache-2.0} is REFUSED
  before any download or load (ADR-006, ADR-298).
* **Lazy load.** Models are loaded only when their measurements are
  requested. Failure to load one model never aborts the others.
* **Deterministic.** Corpus is sorted; cache keys derive from (model id,
  corpus hash). Re-runs of unchanged inputs reuse cached results.
* **Adapter pattern.** Each model family (bi-encoder, reranker, LLM)
  implements :class:`RoutingAdapter` so the harness core stays uniform.

Public surface
--------------
* :class:`BenchmarkHarness` — `run(models_cfg, corpus, output_dir)`
* :class:`BenchmarkReport` — per-model metrics + comparison
* :class:`RoutingAdapter` — Protocol implemented by adapters
* :func:`load_models_manifest`, :func:`load_corpus`
* :func:`license_is_permitted`, :func:`enforce_license_gate`

CLI: invoked from `scripts/cos-routing-benchmark` or
`python3 -m lib.routing_benchmark`.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import logging
import os
import resource
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PERMITTED_LICENSES: frozenset[str] = frozenset(
    {
        "mit",
        "bsd",
        "bsd-2-clause",
        "bsd-3-clause",
        "apache",
        "apache-2.0",
        "apache2",
        "apache 2.0",
    }
)

REPORT_SCHEMA_VERSION = "routing-benchmark-report/v1"
CORPUS_SCHEMA_VERSION = "routing-benchmark-corpus/v1"
MODELS_SCHEMA_VERSION = "routing-benchmark-models/v1"

CACHE_DIR_DEFAULT = Path(".cognitive-os/cache/routing-benchmark")
LANGUAGES = ("en",)
WARM_QUERY_COUNT = 200

# Exit codes
EXIT_OK = 0
EXIT_GENERAL_ERROR = 1
EXIT_LICENSE_VIOLATION = 2


# ---------------------------------------------------------------------------
# License gate
# ---------------------------------------------------------------------------


def license_is_permitted(license_str: str | None) -> bool:
    """True iff the license is in the permit-list (MIT/BSD/Apache family)."""
    if not license_str:
        return False
    return license_str.strip().lower() in PERMITTED_LICENSES


class LicenseViolation(RuntimeError):
    """Raised when a model entry declares a non-permitted license."""


def enforce_license_gate(model_entry: Dict[str, Any]) -> None:
    """Raise :class:`LicenseViolation` if ``model_entry`` is not permitted."""
    lic = model_entry.get("license")
    if not license_is_permitted(lic):
        raise LicenseViolation(
            f"model '{model_entry.get('id', '?')}' declares license "
            f"'{lic}', which is NOT in the permitted set "
            f"(MIT/BSD/Apache). Refusing to benchmark per ADR-298/ADR-006."
        )


# ---------------------------------------------------------------------------
# Manifest + corpus loaders
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Dict[str, Any]:
    import yaml  # type: ignore

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top-level must be a mapping")
    return data


def load_models_manifest(path: Path) -> List[Dict[str, Any]]:
    """Parse the models manifest, validate schema, return entries."""
    data = _load_yaml(path)
    if data.get("schema_version") != MODELS_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version must be {MODELS_SCHEMA_VERSION!r}, "
            f"got {data.get('schema_version')!r}"
        )
    models = data.get("models") or []
    if not isinstance(models, list) or not models:
        raise ValueError(f"{path}: 'models' must be a non-empty list")
    seen_ids: set[str] = set()
    for entry in models:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: each model entry must be a mapping")
        for key in ("id", "adapter", "model_name", "license", "role"):
            if key not in entry:
                raise ValueError(
                    f"{path}: model entry missing required key {key!r}: {entry!r}"
                )
        mid = entry["id"]
        if mid in seen_ids:
            raise ValueError(f"{path}: duplicate model id {mid!r}")
        seen_ids.add(mid)
    return models


def load_corpus(path: Path) -> Dict[str, Dict[str, Any]]:
    """Parse the prompt corpus and return ``{skill: {description, prompts}}``."""
    data = _load_yaml(path)
    if data.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version must be {CORPUS_SCHEMA_VERSION!r}, "
            f"got {data.get('schema_version')!r}"
        )
    skills = data.get("skills") or {}
    if not isinstance(skills, dict) or not skills:
        raise ValueError(f"{path}: 'skills' must be a non-empty mapping")
    out: Dict[str, Dict[str, Any]] = {}
    for skill_name in sorted(skills.keys()):
        entry = skills[skill_name]
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: skill {skill_name!r} must be a mapping")
        desc = (entry.get("description") or "").strip()
        prompts_raw = entry.get("prompts") or {}
        if not isinstance(prompts_raw, dict):
            raise ValueError(f"{path}: skill {skill_name!r} 'prompts' must be a mapping")
        prompts: Dict[str, List[str]] = {}
        for lang in LANGUAGES:
            vals = prompts_raw.get(lang) or []
            if not isinstance(vals, list):
                raise ValueError(
                    f"{path}: skill {skill_name!r} prompts.{lang} must be a list"
                )
            prompts[lang] = [str(v).strip() for v in vals if str(v).strip()]
        out[skill_name] = {"description": desc, "prompts": prompts}
    return out


def corpus_signature(corpus: Dict[str, Dict[str, Any]]) -> str:
    """Stable hash of the corpus content — used as cache key."""
    serialised = json.dumps(corpus, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialised.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


class RoutingAdapter(Protocol):
    """Protocol every benchmark adapter must satisfy."""

    model_id: str
    model_name: str
    role: str

    def load(self) -> None:
        """Download (if needed) and load the model into memory."""

    def predict(
        self, prompt: str, candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        """Score each candidate for ``prompt``.

        ``candidates`` is a list of ``(skill_name, description)`` tuples.
        Returns ``(skill_name, score)`` sorted by score descending.
        """

    def unload(self) -> None:
        """Free model memory."""


# ---------------------------------------------------------------------------
# Concrete adapters
# ---------------------------------------------------------------------------


class FastembedBiEncoderAdapter:
    """Adapter for any FastEmbed-compatible bi-encoder.

    Embeds the query and every candidate description; ranks by cosine
    similarity. Catalog embeddings are computed once on first ``predict``.
    """

    def __init__(self, model_id: str, model_name: str, role: str = "bi-encoder"):
        self.model_id = model_id
        self.model_name = model_name
        self.role = role
        self._model: Any = None
        self._catalog_matrix: Any = None
        self._catalog_skills: List[str] = []
        self._catalog_signature: Optional[str] = None

    def load(self) -> None:
        if self._model is not None:
            return
        try:
            from fastembed import TextEmbedding  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"fastembed unavailable: {exc}") from exc
        self._model = TextEmbedding(model_name=self.model_name)

    def _ensure_catalog(self, candidates: List[Tuple[str, str]]) -> None:
        sig = hashlib.sha256(
            json.dumps(candidates, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if self._catalog_signature == sig and self._catalog_matrix is not None:
            return
        import numpy as np  # type: ignore

        texts = [desc or name for (name, desc) in candidates]
        vecs = list(self._model.embed(texts))
        mat = np.asarray(vecs, dtype=np.float32)
        # L2 normalise.
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._catalog_matrix = mat / norms
        self._catalog_skills = [name for (name, _desc) in candidates]
        self._catalog_signature = sig

    def predict(
        self, prompt: str, candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        if self._model is None:
            self.load()
        assert self._model is not None
        self._ensure_catalog(candidates)
        import numpy as np  # type: ignore

        q_vec = list(self._model.embed([prompt]))[0]
        q = np.asarray(q_vec, dtype=np.float32)
        q_norm = float(np.linalg.norm(q))
        if q_norm == 0:
            return [(name, 0.0) for name in self._catalog_skills]
        q = q / q_norm
        sims = (self._catalog_matrix @ q).tolist()
        ranked = sorted(
            zip(self._catalog_skills, sims),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return [(s, float(v)) for s, v in ranked]

    def unload(self) -> None:
        self._model = None
        self._catalog_matrix = None
        self._catalog_skills = []
        self._catalog_signature = None
        gc.collect()


ONNX_CACHE_DIR_DEFAULT = Path(".cognitive-os/cache/onnx-models")


def _onnx_cache_path(model_name: str, revision: str) -> Path:
    """Revision-aware cache dir so multiple revisions of one repo coexist."""
    key = hashlib.sha256(f"{model_name}@{revision}".encode("utf-8")).hexdigest()[:32]
    return ONNX_CACHE_DIR_DEFAULT / key


class OnnxDirectBiEncoderAdapter:
    """Adapter for HF-hosted ONNX models not in FastEmbed's registry (ADR-301).

    Downloads ``model.onnx`` + tokenizer files from huggingface.co lazily on
    first use. Caches under ``.cognitive-os/cache/onnx-models/<hash>/``.
    Uses onnxruntime CPU provider. Mean-pooled, L2-normalised embeddings —
    same contract as :class:`FastembedBiEncoderAdapter`.
    """

    def __init__(
        self,
        model_id: str,
        model_name: str,
        role: str = "bi-encoder",
        *,
        onnx_subpath: str = "model.onnx",
        revision: str = "main",
    ):
        self.model_id = model_id
        self.model_name = model_name
        self.role = role
        self.onnx_subpath = onnx_subpath
        self.revision = revision
        self._session: Any = None
        self._tokenizer: Any = None
        self._catalog_matrix: Any = None
        self._catalog_skills: List[str] = []
        self._catalog_signature: Optional[str] = None
        self._model_dir: Optional[Path] = None

    # ------------------------------------------------------------------ cache
    def cache_dir(self) -> Path:
        return _onnx_cache_path(self.model_name, self.revision)

    # ------------------------------------------------------------------- load
    def load(self) -> None:
        if self._session is not None:
            return
        try:
            from huggingface_hub import hf_hub_download  # type: ignore
            import onnxruntime as ort  # type: ignore
            from tokenizers import Tokenizer  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time failure
            raise RuntimeError(
                f"onnx-direct deps unavailable: {exc}"
            ) from exc

        cache_dir = self.cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Resolve sibling directory of the .onnx file for tokenizer lookups.
        onnx_dir_in_repo = ""
        if "/" in self.onnx_subpath:
            onnx_dir_in_repo = self.onnx_subpath.rsplit("/", 1)[0]

        def _fetch(filename: str, *, required: bool) -> Optional[str]:
            try:
                return hf_hub_download(
                    repo_id=self.model_name,
                    filename=filename,
                    revision=self.revision,
                    cache_dir=str(cache_dir),
                )
            except Exception as exc:
                if required:
                    raise RuntimeError(
                        f"hf download failed for {self.model_name}:{filename} "
                        f"@ {self.revision}: {exc}"
                    ) from exc
                LOGGER.debug("optional file missing %s: %s", filename, exc)
                return None

        # Required: ONNX weights file.
        onnx_path = _fetch(self.onnx_subpath, required=True)
        if onnx_path is None:
            raise RuntimeError(f"no ONNX model found for {self.model_name}@{self.revision}")
        # External-data sidecar (e.g. BGE-M3's model.onnx_data). Optional.
        _fetch(self.onnx_subpath + "_data", required=False)

        # Tokenizer files. Try the onnx/ subdir first, fall back to repo root.
        tok_filename: Optional[str] = None
        for candidate in (
            f"{onnx_dir_in_repo}/tokenizer.json" if onnx_dir_in_repo else "tokenizer.json",
            "tokenizer.json",
        ):
            path = _fetch(candidate, required=False)
            if path is not None:
                tok_filename = path
                break
        if tok_filename is None:
            raise RuntimeError(
                f"no tokenizer.json found for {self.model_name}@{self.revision}"
            )

        # Best-effort fetch of accompanying tokenizer metadata.
        for extra in ("tokenizer_config.json", "special_tokens_map.json", "sentencepiece.bpe.model"):
            for candidate in (
                f"{onnx_dir_in_repo}/{extra}" if onnx_dir_in_repo else extra,
                extra,
            ):
                if _fetch(candidate, required=False) is not None:
                    break

        self._tokenizer = Tokenizer.from_file(tok_filename)
        self._session = ort.InferenceSession(
            onnx_path, providers=["CPUExecutionProvider"]
        )
        self._model_dir = Path(onnx_path).parent

    # --------------------------------------------------------------- encoding
    def _encode(self, texts: List[str]) -> Any:
        import numpy as np  # type: ignore

        encodings = self._tokenizer.encode_batch(texts)
        # Pad to longest in batch.
        max_len = max((len(e.ids) for e in encodings), default=1)
        input_ids = np.zeros((len(encodings), max_len), dtype=np.int64)
        attention_mask = np.zeros((len(encodings), max_len), dtype=np.int64)
        for i, enc in enumerate(encodings):
            ids = enc.ids[:max_len]
            input_ids[i, : len(ids)] = ids
            attention_mask[i, : len(ids)] = 1

        feed: Dict[str, Any] = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        # Some ONNX exports also expect token_type_ids.
        input_names = {inp.name for inp in self._session.get_inputs()}
        if "token_type_ids" in input_names:
            feed["token_type_ids"] = np.zeros_like(input_ids)
        # Only pass declared inputs.
        feed = {k: v for k, v in feed.items() if k in input_names}

        outputs = self._session.run(None, feed)
        last_hidden = outputs[0]  # (batch, seq, hidden)
        mask = attention_mask.astype(np.float32)[:, :, None]
        summed = (last_hidden * mask).sum(axis=1)
        denom = mask.sum(axis=1)
        denom[denom == 0] = 1.0
        pooled = summed / denom
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return pooled / norms

    def _ensure_catalog(self, candidates: List[Tuple[str, str]]) -> None:
        sig = hashlib.sha256(
            json.dumps(candidates, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if self._catalog_signature == sig and self._catalog_matrix is not None:
            return
        texts = [desc or name for (name, desc) in candidates]
        self._catalog_matrix = self._encode(texts)
        self._catalog_skills = [name for (name, _desc) in candidates]
        self._catalog_signature = sig

    def predict(
        self, prompt: str, candidates: List[Tuple[str, str]]
    ) -> List[Tuple[str, float]]:
        if self._session is None:
            self.load()
        self._ensure_catalog(candidates)

        q = self._encode([prompt])[0]
        sims = (self._catalog_matrix @ q).tolist()
        ranked = sorted(
            zip(self._catalog_skills, sims),
            key=lambda kv: kv[1],
            reverse=True,
        )
        return [(s, float(v)) for s, v in ranked]

    def unload(self) -> None:
        self._session = None
        self._tokenizer = None
        self._catalog_matrix = None
        self._catalog_skills = []
        self._catalog_signature = None
        gc.collect()


def _build_fastembed(model_id, model_name, role, **_kw):
    return FastembedBiEncoderAdapter(model_id, model_name, role)


def _build_onnx_direct(model_id, model_name, role, **kw):
    return OnnxDirectBiEncoderAdapter(
        model_id,
        model_name,
        role,
        onnx_subpath=kw.get("onnx_subpath", "model.onnx"),
        revision=kw.get("revision", "main"),
    )


# Registry: adapter_kind -> factory(model_id, model_name, role, **kw)
_ADAPTER_REGISTRY: Dict[str, Callable[..., RoutingAdapter]] = {
    "fastembed-bi-encoder": _build_fastembed,
    "onnx-direct-bi-encoder": _build_onnx_direct,
}


def build_adapter(entry: Dict[str, Any]) -> RoutingAdapter:
    """Construct an adapter for ``entry`` — license-gated."""
    enforce_license_gate(entry)
    kind = entry["adapter"]
    factory = _ADAPTER_REGISTRY.get(kind)
    if factory is None:
        raise ValueError(
            f"unknown adapter kind {kind!r} for model {entry.get('id')!r}. "
            f"Known adapters: {sorted(_ADAPTER_REGISTRY)}"
        )
    return factory(
        entry["id"],
        entry["model_name"],
        entry.get("role", "bi-encoder"),
        onnx_subpath=entry.get("onnx_subpath", "model.onnx"),
        revision=entry.get("revision", "main"),
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass
class PerLangMetric:
    language: str
    queries: int
    precision_at_1: float
    precision_at_5: float
    mrr: float


@dataclass
class ModelMetric:
    model_id: str
    model_name: str
    adapter: str
    license: str
    role: str
    license_ok: bool
    loaded: bool
    load_error: Optional[str]
    total_queries: int
    failures: int
    precision_at_1: float
    precision_at_5: float
    mrr: float
    cold_start_ms: float
    warm_p50_ms: float
    warm_p95_ms: float
    warm_p99_ms: float
    peak_rss_mb: float
    model_size_mb: float
    per_language: List[PerLangMetric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class BenchmarkReport:
    schema_version: str
    timestamp: str
    environment: Dict[str, Any]
    corpus_signature: str
    corpus_skills: int
    corpus_prompts: int
    models: List[ModelMetric]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "environment": self.environment,
            "corpus_signature": self.corpus_signature,
            "corpus_skills": self.corpus_skills,
            "corpus_prompts": self.corpus_prompts,
            "models": [m.to_dict() for m in self.models],
        }


# ---------------------------------------------------------------------------
# Helpers — RSS, model size, environment
# ---------------------------------------------------------------------------


def _peak_rss_mb() -> float:
    """Return current peak RSS in MB. ru_maxrss is bytes on macOS, KB on Linux."""
    try:
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        return 0.0
    if sys.platform == "darwin":
        return rss / (1024 * 1024)
    return rss / 1024  # Linux: KB -> MB


def _dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total / (1024 * 1024)


def _fastembed_cache_path(model_name: str) -> Path:
    """Best-effort guess of fastembed's local cache directory for a model."""
    base = Path(os.environ.get("FASTEMBED_CACHE_PATH", Path.home() / ".cache" / "fastembed"))
    slug = model_name.replace("/", "_")
    candidates = [base, base / "fastembed_cache", base / slug]
    best = 0.0
    chosen = base
    for c in candidates:
        if c.exists():
            size = _dir_size_mb(c)
            if size > best:
                best = size
                chosen = c
    return chosen


def _environment_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
    }
    try:
        import fastembed  # type: ignore

        snap["fastembed_version"] = getattr(fastembed, "__version__", "unknown")
    except Exception:
        snap["fastembed_version"] = None
    try:
        import numpy  # type: ignore

        snap["numpy_version"] = numpy.__version__
    except Exception:
        snap["numpy_version"] = None
    return snap


# ---------------------------------------------------------------------------
# Benchmark harness
# ---------------------------------------------------------------------------


@dataclass
class _Query:
    prompt: str
    expected_skill: str
    language: str


def _flatten_queries(
    corpus: Dict[str, Dict[str, Any]],
    quick: bool = False,
) -> List[_Query]:
    """Flatten the corpus into a deterministic list of ``_Query``."""
    out: List[_Query] = []
    skills_sorted = sorted(corpus.keys())
    if quick:
        # Sample up to 20 skills for fast iteration.
        skills_sorted = skills_sorted[:20]
    for skill in skills_sorted:
        prompts_by_lang = corpus[skill]["prompts"]
        langs = LANGUAGES
        for lang in langs:
            for prompt in prompts_by_lang.get(lang, []):
                out.append(_Query(prompt=prompt, expected_skill=skill, language=lang))
    return out


class BenchmarkHarness:
    """Coordinator. Loads models lazily, runs queries, writes the report."""

    def __init__(
        self,
        models_manifest_path: Path,
        corpus_path: Path,
        *,
        cache_dir: Optional[Path] = None,
        warm_queries: int = WARM_QUERY_COUNT,
        adapter_factory: Optional[Callable[[Dict[str, Any]], RoutingAdapter]] = None,
    ):
        self.models_manifest_path = models_manifest_path
        self.corpus_path = corpus_path
        self.cache_dir = cache_dir or CACHE_DIR_DEFAULT
        self.warm_queries = warm_queries
        self._adapter_factory = adapter_factory or build_adapter

    # ------------------------------------------------------------------ run
    def run(
        self,
        *,
        model_ids: Optional[List[str]] = None,
        quick: bool = False,
        strict: bool = False,
    ) -> BenchmarkReport:
        manifest = load_models_manifest(self.models_manifest_path)
        if model_ids:
            wanted = set(model_ids)
            manifest = [m for m in manifest if m["id"] in wanted]
            missing = wanted - {m["id"] for m in manifest}
            if missing:
                raise ValueError(
                    f"model ids not in manifest: {sorted(missing)}"
                )
        corpus = load_corpus(self.corpus_path)
        sig = corpus_signature(corpus)
        queries = _flatten_queries(corpus, quick=quick)
        total_prompts = sum(
            len(prompts)
            for entry in corpus.values()
            for prompts in entry["prompts"].values()
        )

        # Candidate list passed to each adapter.
        candidates = [
            (skill, entry["description"]) for skill, entry in sorted(corpus.items())
        ]

        metrics: List[ModelMetric] = []
        for entry in manifest:
            metric = self._benchmark_one(
                entry, queries, candidates, strict=strict
            )
            metrics.append(metric)

        report = BenchmarkReport(
            schema_version=REPORT_SCHEMA_VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=_environment_snapshot(),
            corpus_signature=sig,
            corpus_skills=len(corpus),
            corpus_prompts=total_prompts,
            models=metrics,
        )
        return report

    # ------------------------------------------------- per-model benchmark
    def _benchmark_one(
        self,
        entry: Dict[str, Any],
        queries: List[_Query],
        candidates: List[Tuple[str, str]],
        *,
        strict: bool,
    ) -> ModelMetric:
        mid = entry["id"]
        # License gate first — never load if not permitted.
        license_ok = license_is_permitted(entry.get("license"))
        if not license_ok:
            msg = (
                f"license {entry.get('license')!r} not permitted "
                f"(allowed: MIT/BSD/Apache)"
            )
            if strict:
                raise LicenseViolation(f"model {mid!r}: {msg}")
            LOGGER.warning("skipping model %s: %s", mid, msg)
            return ModelMetric(
                model_id=mid,
                model_name=entry["model_name"],
                adapter=entry["adapter"],
                license=str(entry.get("license", "")),
                role=entry.get("role", ""),
                license_ok=False,
                loaded=False,
                load_error=msg,
                total_queries=0,
                failures=0,
                precision_at_1=0.0,
                precision_at_5=0.0,
                mrr=0.0,
                cold_start_ms=0.0,
                warm_p50_ms=0.0,
                warm_p95_ms=0.0,
                warm_p99_ms=0.0,
                peak_rss_mb=0.0,
                model_size_mb=0.0,
            )

        # Cache lookup.
        cached = self._load_cache(entry, queries)
        if cached is not None:
            return cached

        try:
            adapter = self._adapter_factory(entry)
        except (LicenseViolation, ValueError) as exc:
            if strict and isinstance(exc, LicenseViolation):
                raise
            LOGGER.warning("adapter build failed for %s: %s", mid, exc)
            return self._failed_metric(entry, str(exc))

        # Cold start.
        cold_t0 = time.perf_counter()
        try:
            adapter.load()
            # Force catalog embedding now so cold-start captures everything.
            adapter.predict("warm-up prompt", candidates)
        except Exception as exc:
            LOGGER.warning("model load failed for %s: %s", mid, exc)
            return self._failed_metric(entry, f"load failed: {exc}")
        cold_start_ms = (time.perf_counter() - cold_t0) * 1000

        # Warm queries — accuracy + latency.
        latencies_ms: List[float] = []
        failures = 0
        hits_at_1 = 0
        hits_at_5 = 0
        reciprocal_ranks: List[float] = []
        per_lang_counters: Dict[str, Dict[str, float]] = {
            lg: {"q": 0, "p1": 0, "p5": 0, "rr_sum": 0.0} for lg in LANGUAGES
        }

        # If queries < warm_queries, we cycle to reach the requested count
        # for latency stats; accuracy is measured over the unique queries.
        unique_queries = queries
        latency_target = min(self.warm_queries, max(len(queries), 1))

        for q in unique_queries:
            t0 = time.perf_counter()
            try:
                ranked = adapter.predict(q.prompt, candidates)
            except Exception as exc:
                failures += 1
                LOGGER.debug("predict failed: %s", exc)
                continue
            latencies_ms.append((time.perf_counter() - t0) * 1000)
            top_skill = ranked[0][0] if ranked else None
            top_5 = {name for name, _ in ranked[:5]}
            rank = next(
                (i + 1 for i, (name, _) in enumerate(ranked) if name == q.expected_skill),
                0,
            )
            rr = (1.0 / rank) if rank > 0 else 0.0
            reciprocal_ranks.append(rr)
            lc = per_lang_counters[q.language]
            lc["q"] += 1
            lc["rr_sum"] += rr
            if top_skill == q.expected_skill:
                hits_at_1 += 1
                lc["p1"] += 1
            if q.expected_skill in top_5:
                hits_at_5 += 1
                lc["p5"] += 1

        # Top up latency samples if needed (re-running first query).
        while len(latencies_ms) < latency_target and unique_queries:
            q = unique_queries[len(latencies_ms) % len(unique_queries)]
            t0 = time.perf_counter()
            try:
                adapter.predict(q.prompt, candidates)
            except Exception:
                break
            latencies_ms.append((time.perf_counter() - t0) * 1000)

        n = max(1, len(unique_queries) - failures)
        p1 = hits_at_1 / n
        p5 = hits_at_5 / n
        mrr = sum(reciprocal_ranks) / n if reciprocal_ranks else 0.0
        p50 = _percentile(latencies_ms, 50)
        p95 = _percentile(latencies_ms, 95)
        p99 = _percentile(latencies_ms, 99)

        per_lang: List[PerLangMetric] = []
        for lg in LANGUAGES:
            lc = per_lang_counters[lg]
            qn = int(lc["q"]) or 1
            per_lang.append(
                PerLangMetric(
                    language=lg,
                    queries=int(lc["q"]),
                    precision_at_1=lc["p1"] / qn if lc["q"] else 0.0,
                    precision_at_5=lc["p5"] / qn if lc["q"] else 0.0,
                    mrr=lc["rr_sum"] / qn if lc["q"] else 0.0,
                )
            )

        size_mb = _dir_size_mb(_fastembed_cache_path(entry["model_name"]))
        metric = ModelMetric(
            model_id=mid,
            model_name=entry["model_name"],
            adapter=entry["adapter"],
            license=str(entry["license"]),
            role=entry.get("role", ""),
            license_ok=True,
            loaded=True,
            load_error=None,
            total_queries=len(unique_queries),
            failures=failures,
            precision_at_1=p1,
            precision_at_5=p5,
            mrr=mrr,
            cold_start_ms=cold_start_ms,
            warm_p50_ms=p50,
            warm_p95_ms=p95,
            warm_p99_ms=p99,
            peak_rss_mb=_peak_rss_mb(),
            model_size_mb=size_mb,
            per_language=per_lang,
        )

        # Persist cache.
        self._save_cache(entry, queries, metric)
        adapter.unload()
        return metric

    # ------------------------------------------------------------ cache I/O
    def _cache_key(self, entry: Dict[str, Any], queries: List[_Query]) -> Path:
        h = hashlib.sha256()
        h.update(json.dumps(entry, sort_keys=True).encode())
        h.update(
            json.dumps(
                [(q.prompt, q.expected_skill, q.language) for q in queries],
                sort_keys=True,
            ).encode()
        )
        return self.cache_dir / f"{entry['id']}-{h.hexdigest()[:16]}.json"

    def _load_cache(
        self, entry: Dict[str, Any], queries: List[_Query]
    ) -> Optional[ModelMetric]:
        path = self._cache_key(entry, queries)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        per_lang = [PerLangMetric(**pl) for pl in data.get("per_language", [])]
        data["per_language"] = per_lang
        try:
            return ModelMetric(**data)
        except TypeError:
            return None

    def _save_cache(
        self,
        entry: Dict[str, Any],
        queries: List[_Query],
        metric: ModelMetric,
    ) -> None:
        path = self._cache_key(entry, queries)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metric.to_dict(), indent=2), encoding="utf-8")

    def _failed_metric(
        self, entry: Dict[str, Any], err: str
    ) -> ModelMetric:
        return ModelMetric(
            model_id=entry["id"],
            model_name=entry["model_name"],
            adapter=entry["adapter"],
            license=str(entry.get("license", "")),
            role=entry.get("role", ""),
            license_ok=license_is_permitted(entry.get("license")),
            loaded=False,
            load_error=err,
            total_queries=0,
            failures=0,
            precision_at_1=0.0,
            precision_at_5=0.0,
            mrr=0.0,
            cold_start_ms=0.0,
            warm_p50_ms=0.0,
            warm_p95_ms=0.0,
            warm_p99_ms=0.0,
            peak_rss_mb=0.0,
            model_size_mb=0.0,
        )


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def write_report_json(report: BenchmarkReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_report_markdown(report: BenchmarkReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Routing Model Benchmark Report")
    lines.append("")
    lines.append(f"- Generated: {report.timestamp}")
    lines.append(f"- Schema: `{report.schema_version}`")
    lines.append(f"- Corpus signature: `{report.corpus_signature}`")
    lines.append(
        f"- Corpus: {report.corpus_skills} skills, {report.corpus_prompts} prompts"
    )
    lines.append("")
    lines.append("## Environment")
    lines.append("")
    for k, v in sorted(report.environment.items()):
        lines.append(f"- {k}: `{v}`")
    lines.append("")
    lines.append("## Comparison")
    lines.append("")
    lines.append(
        "| model | role | precision@1 | precision@5 | MRR | warm p95 ms | "
        "cold start ms | peak MB | size MB | license | loaded |"
    )
    lines.append(
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |"
    )
    for m in report.models:
        lines.append(
            "| {id} | {role} | {p1:.3f} | {p5:.3f} | {mrr:.3f} | "
            "{p95:.1f} | {cold:.1f} | {rss:.1f} | {size:.1f} | {lic} | {ok} |".format(
                id=m.model_id,
                role=m.role,
                p1=m.precision_at_1,
                p5=m.precision_at_5,
                mrr=m.mrr,
                p95=m.warm_p95_ms,
                cold=m.cold_start_ms,
                rss=m.peak_rss_mb,
                size=m.model_size_mb,
                lic=m.license,
                ok="yes" if m.loaded else "no",
            )
        )
    lines.append("")
    lines.append("## Per-Language Precision@1")
    lines.append("")
    header = "| model | " + " | ".join(LANGUAGES) + " |"
    sep = "| --- |" + " ---: |" * len(LANGUAGES)
    lines.append(header)
    lines.append(sep)
    for m in report.models:
        if not m.loaded:
            continue
        cells = []
        by_lang = {pl.language: pl for pl in m.per_language}
        for lg in LANGUAGES:
            pl = by_lang.get(lg)
            cells.append(f"{pl.precision_at_1:.3f}" if pl else "—")
        lines.append("| " + m.model_id + " | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## Failure Modes")
    lines.append("")
    lines.append("| model | loaded | failures | load_error |")
    lines.append("| --- | --- | ---: | --- |")
    for m in report.models:
        # Python 3.11 forbids backslash inside f-string expression; escape outside.
        load_error = (m.load_error or "").replace("|", r"\|")
        loaded_str = "yes" if m.loaded else "no"
        lines.append(
            f"| {m.model_id} | {loaded_str} | {m.failures} | {load_error} |"
        )
    lines.append("")
    lines.append("## Recommendation Block")
    lines.append("")
    loaded = [m for m in report.models if m.loaded]
    if not loaded:
        lines.append("_No model loaded successfully — nothing to recommend._")
    else:
        best_p1 = max(loaded, key=lambda m: m.precision_at_1)
        best_lat = min(loaded, key=lambda m: m.warm_p95_ms or float("inf"))
        best_mrr = max(loaded, key=lambda m: m.mrr)
        lines.append(
            f"- Best precision@1: **{best_p1.model_id}** "
            f"({best_p1.precision_at_1:.3f})"
        )
        lines.append(
            f"- Best latency (warm p95): **{best_lat.model_id}** "
            f"({best_lat.warm_p95_ms:.1f} ms)"
        )
        lines.append(
            f"- Best MRR: **{best_mrr.model_id}** ({best_mrr.mrr:.3f})"
        )
    lines.append("")
    lines.append(
        "_Generated by `lib/routing_benchmark.py` (ADR-298). "
        "Every model-selection ADR MUST cite a report produced by this harness._"
    )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Corpus regenerator (LLM-assisted) — ADR-049 dispatch
# ---------------------------------------------------------------------------


def regenerate_corpus(
    skills_root: Path,
    package_skills_root: Path,
    output_path: Path,
    *,
    dispatch_fn: Optional[Callable[..., Any]] = None,
    max_skills: Optional[int] = None,
) -> int:
    """Walk SKILL.md files, ask the LLM dispatcher to draft English prompts.

    Returns the number of skills written. ``dispatch_fn`` is injected for
    tests; defaults to ``lib.dispatch.dispatch``. Output is deterministic:
    skills sorted, prompts trimmed and stripped.
    """
    import yaml  # type: ignore

    skill_md_paths: Dict[str, Path] = {}
    for root in (skills_root, package_skills_root):
        if not root.exists():
            continue
        for p in root.rglob("SKILL.md"):
            # name = directory containing SKILL.md
            name = p.parent.name
            if name in skill_md_paths:
                continue
            skill_md_paths[name] = p

    if max_skills is not None:
        keep = sorted(skill_md_paths)[:max_skills]
        skill_md_paths = {k: skill_md_paths[k] for k in keep}

    out: Dict[str, Any] = {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "skills": {},
    }
    if dispatch_fn is None:
        from lib.dispatch import dispatch as _dispatch  # type: ignore

        dispatch_fn = _dispatch

    for name in sorted(skill_md_paths):
        path = skill_md_paths[name]
        desc = _parse_description(path)
        if not desc:
            continue
        prompt_template = (
            "Generate 3 short English user prompts that a user would write "
            f"to invoke a skill described as: '{desc}'. Return strict YAML "
            "with key en; its value is a list of strings. No prose."
        )
        try:
            result = dispatch_fn(prompt=prompt_template, task_type="general")
            text = getattr(result, "text", None) or getattr(result, "output", "")
            parsed = yaml.safe_load(text) if text else {}
        except Exception:
            parsed = {}
        prompts: Dict[str, List[str]] = {}
        for lg in LANGUAGES:
            vals = (parsed or {}).get(lg) or []
            if isinstance(vals, str):
                vals = [vals]
            prompts[lg] = [str(v).strip() for v in vals if str(v).strip()]
        out["skills"][name] = {
            "description": desc,
            "prompts": prompts,
        }

    header = (
        "# SCOPE: os-only\n"
        "# AUTO-GENERATED via lib.routing_benchmark.regenerate_corpus.\n"
        "# Refine manually — the harness measures regressions, not absolute truth.\n"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        header + yaml.safe_dump(out, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
    return len(out["skills"])


def _parse_description(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    import yaml  # type: ignore

    lines = text.splitlines()
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if start is None:
                start = i
            else:
                end = i
                break
    if start is None or end is None:
        return ""
    front = "\n".join(lines[start + 1 : end])
    try:
        data = yaml.safe_load(front) or {}
    except Exception:
        return ""
    return str(data.get("description") or "").strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="cos-routing-benchmark",
        description=(
            "Benchmark candidate routing models (ADR-298). Every model-"
            "selection ADR MUST cite a report produced by this harness."
        ),
    )
    p.add_argument(
        "--models",
        default=None,
        help="Comma-separated model ids (default: all in manifest)",
    )
    p.add_argument(
        "--models-manifest",
        default="manifests/routing-benchmark-models.yaml",
    )
    p.add_argument(
        "--corpus",
        default="manifests/routing-benchmark-corpus.yaml",
    )
    p.add_argument(
        "--output",
        default="docs/06-Daily/reports",
        help="Output directory for the .md and .json artefacts",
    )
    p.add_argument(
        "--quick",
        action="store_true",
        help="Sample 20 skills for fast iteration",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit 2 if any model fails the license gate",
    )
    p.add_argument(
        "--regenerate-corpus",
        action="store_true",
        help="Walk SKILL.md files, dispatch LLM, write a fresh corpus.",
    )
    p.add_argument(
        "--max-skills",
        type=int,
        default=None,
        help="Cap on skills when regenerating (for cost control)",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=os.environ.get("COS_BENCHMARK_LOG", "INFO"),
        format="%(levelname)s %(message)s",
    )
    args = _parse_args(argv or sys.argv[1:])

    if args.regenerate_corpus:
        count = regenerate_corpus(
            skills_root=Path("skills"),
            package_skills_root=Path("packages"),
            output_path=Path(args.corpus),
            max_skills=args.max_skills,
        )
        print(f"wrote {count} skills to {args.corpus}")
        return EXIT_OK

    model_ids = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models
        else None
    )

    harness = BenchmarkHarness(
        models_manifest_path=Path(args.models_manifest),
        corpus_path=Path(args.corpus),
    )
    try:
        report = harness.run(
            model_ids=model_ids, quick=args.quick, strict=args.strict
        )
    except LicenseViolation as exc:
        print(f"LICENSE GATE: {exc}", file=sys.stderr)
        return EXIT_LICENSE_VIOLATION
    except Exception as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return EXIT_GENERAL_ERROR

    # Refuse to write artefacts if every model failed the license gate
    # under --strict (already raised above) — but if --strict is off and
    # the only requested model is blocked, exit 2 for CI clarity.
    if args.strict and any(not m.license_ok for m in report.models):
        print("LICENSE GATE: one or more models failed", file=sys.stderr)
        return EXIT_LICENSE_VIOLATION

    out_dir = Path(args.output)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md_path = out_dir / f"routing-benchmark-{date}.md"
    json_path = out_dir / f"routing-benchmark-{date}.json"
    write_report_markdown(report, md_path)
    write_report_json(report, json_path)
    print(f"wrote {md_path}")
    print(f"wrote {json_path}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
