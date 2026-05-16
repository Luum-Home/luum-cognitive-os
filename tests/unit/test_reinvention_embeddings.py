"""Tests for the EmbeddingsIndex (ADR-029b Phase B-beta, ADR-039).

sentence-transformers is OPTIONAL. These tests MOCK the module so CI never
downloads or loads a real model. Six cases cover:

1. ImportError fallback when sentence-transformers is absent.
2. Build index produces embeddings and persists artefacts.
3. Load round-trip (build → load new instance → same items).
4. find_similar returns top-k sorted by cosine desc, above min_score.
5. find_similar on empty / unbuilt index returns [].
6. Hook-style graceful fallback: missing module does not crash callers.
"""
from __future__ import annotations

import sys
import textwrap
import types
import json
from pathlib import Path

import pytest


# ---------- shared fake sentence_transformers module ----------


def _install_fake_numpy(monkeypatch):
    """Install a tiny numpy substitute sufficient for EmbeddingsIndex tests."""

    class _FakeVector:
        def __init__(self, values):
            self.values = [float(v) for v in values]

        def __add__(self, scalar):
            return _FakeVector([v + float(scalar) for v in self.values])

        def __truediv__(self, scalar):
            return _FakeVector([v / float(scalar) for v in self.values])

        def astype(self, _dtype):
            return _FakeVector(self.values)

        def tolist(self):
            return list(self.values)

        @property
        def shape(self):
            return (len(self.values),)

        def __iter__(self):
            return iter(self.values)

        def __len__(self):
            return len(self.values)

    class _FakeMatrix:
        def __init__(self, rows):
            self.rows = [
                row if isinstance(row, _FakeVector) else _FakeVector(row)
                for row in rows
            ]

        def astype(self, _dtype):
            return _FakeMatrix([row.values for row in self.rows])

        def __getitem__(self, idx):
            return self.rows[idx]

        def __len__(self):
            return len(self.rows)

        @property
        def shape(self):
            cols = len(self.rows[0]) if self.rows else 0
            return (len(self.rows), cols)

        def __matmul__(self, vec):
            return _FakeVector(
                [sum(a * b for a, b in zip(row.values, vec.values)) for row in self.rows]
            )

    def _array(values, dtype=None):  # noqa: ARG001
        return _FakeVector(values)

    def _vstack(rows):
        return _FakeMatrix(rows)

    def _empty(shape, dtype=None):  # noqa: ARG001
        rows, cols = shape
        return _FakeMatrix([[0.0] * cols for _ in range(rows)])

    def _save(path, arr, allow_pickle=False):  # noqa: ARG001
        matrix = arr.rows if isinstance(arr, _FakeMatrix) else [_FakeVector(arr.values)]
        payload = [row.values for row in matrix]
        Path(path).write_text(json.dumps(payload))

    def _load(path):
        return _FakeMatrix(json.loads(Path(path).read_text()))

    def _norm(vec):
        return sum(v * v for v in vec.values) ** 0.5

    fake = types.ModuleType("numpy")
    fake.float32 = "float32"
    fake.array = _array
    fake.vstack = _vstack
    fake.empty = _empty
    fake.save = _save
    fake.load = _load
    fake.linalg = types.SimpleNamespace(norm=_norm)
    monkeypatch.setitem(sys.modules, "numpy", fake)
    return fake

def _install_fake_st(monkeypatch, *, dim: int = 8):
    """Install a fake `sentence_transformers` module into sys.modules.

    The fake SentenceTransformer.encode() returns deterministic unit vectors
    derived from text hashes, so cosine similarity is stable across runs.
    """
    np = _install_fake_numpy(monkeypatch)

    class _FakeModel:
        def __init__(self, name: str):
            self.name = name

        def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True,
                   show_progress_bar=False):
            # Deterministic pseudo-embeddings: word-presence bit vector of
            # fixed dim, normalised. Same text → same vector; overlapping
            # vocabulary → higher cosine.
            if isinstance(texts, str):
                texts = [texts]
            vocab = ["rate", "limit", "token", "agent", "heartbeat", "bus", "verify", "hook"]
            vocab = vocab[:dim]
            rows = []
            for t in texts:
                t_low = t.lower()
                row = np.array([1.0 if w in t_low else 0.0 for w in vocab], dtype=np.float32)
                # Avoid zero-vector; add tiny constant then renormalise.
                row = row + 1e-6
                if normalize_embeddings:
                    n = np.linalg.norm(row)
                    if n > 0:
                        row = row / n
                rows.append(row)
            return np.vstack(rows).astype(np.float32)

    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = _FakeModel
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)
    return fake


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Minimal project tree — same shape as the Jaccard test fixture."""
    (tmp_path / "lib").mkdir()
    (tmp_path / "hooks").mkdir()
    (tmp_path / "scripts").mkdir()

    (tmp_path / "lib" / "rate_limiter.py").write_text(textwrap.dedent('''\
        """Rate Limiter — prevents token flooding and excessive tool usage."""
        class RateLimiter:
            def check(self, action):
                """Return whether the action is allowed."""
                return True
    '''))
    (tmp_path / "lib" / "agent_bus.py").write_text(textwrap.dedent('''\
        """Agent Bus — heartbeat and liveness pings via pub/sub."""
        class AgentBus:
            def publish_heartbeat(self, agent_id):
                """Emit a liveness ping."""
                pass
    '''))
    (tmp_path / "hooks" / "auto-verify.sh").write_text(textwrap.dedent('''\
        #!/usr/bin/env bash
        # Auto verify — runs acceptance checks after agent completion.
        verify_task() { echo "x"; }
    '''))
    return tmp_path


# ---------- tests ----------

def test_import_raises_when_sentence_transformers_absent(monkeypatch):
    """EmbeddingsIndex() MUST raise ImportError if sentence_transformers absent."""
    # Force the import to fail even if the package happens to be installed.
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)

    # Reload the module so the class sees the patched import path.
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    with pytest.raises(ImportError) as exc:
        rs.EmbeddingsIndex()
    assert "sentence-transformers" in str(exc.value)

    # Cleanup: drop the poison so subsequent tests can re-patch cleanly.
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    importlib.reload(rs)


def test_build_and_persist_creates_artefacts(sample_project, monkeypatch):
    _install_fake_st(monkeypatch)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    eidx = rs.EmbeddingsIndex()
    eidx.build_index(sample_project)

    assert len(eidx.items) >= 2, "expected indexable files to produce items"
    assert eidx.embeddings_path is not None
    assert eidx.embeddings_path.is_file(), "embeddings .npy must be persisted"
    assert eidx.meta_path is not None
    assert eidx.meta_path.is_file(), "metadata JSON must be persisted"
    # Embeddings rows match item count.
    import numpy as np

    arr = np.load(str(eidx.embeddings_path))
    assert arr.shape[0] == len(eidx.items)


def test_load_roundtrip_recovers_items(sample_project, monkeypatch):
    _install_fake_st(monkeypatch)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    builder = rs.EmbeddingsIndex()
    builder.build_index(sample_project)
    expected_paths = {it["path"] for it in builder.items}

    loader = rs.EmbeddingsIndex()
    assert loader.load(sample_project) is True
    loaded_paths = {it["path"] for it in loader.items}
    assert loaded_paths == expected_paths
    assert loader.model_name == builder.model_name


def test_find_similar_returns_scored_matches(sample_project, monkeypatch):
    _install_fake_st(monkeypatch)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    eidx = rs.EmbeddingsIndex()
    eidx.build_index(sample_project)

    # Query shares "agent" + "heartbeat" with agent_bus.py → should rank first.
    matches = eidx.find_similar(
        "add lib/agent_heartbeat.py for liveness pings",
        top_k=3,
        min_score=0.0,
    )
    assert matches, "expected at least one match above 0.0"
    paths = [m["path"] for m in matches]
    assert "lib/agent_bus.py" in paths
    # Results must be sorted descending by score.
    scores = [m["score"] for m in matches]
    assert scores == sorted(scores, reverse=True)


def test_find_similar_threshold_filters_low_scores(sample_project, monkeypatch):
    _install_fake_st(monkeypatch)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    eidx = rs.EmbeddingsIndex()
    eidx.build_index(sample_project)

    # Query has no vocabulary overlap with the fake-embedding word list.
    strict = eidx.find_similar("quantum chromodynamics", top_k=5, min_score=0.99)
    assert strict == []


def test_find_similar_empty_index_returns_empty(monkeypatch, tmp_path):
    """Querying before build() returns [] — no crash, no model load."""
    _install_fake_st(monkeypatch)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    eidx = rs.EmbeddingsIndex(
        embeddings_path=tmp_path / "empty.npy",
        meta_path=tmp_path / "empty.json",
    )
    # Never built; _embeddings is None.
    result = eidx.find_similar("anything", top_k=3, min_score=0.0)
    assert result == []


def test_hook_fallback_path_when_embeddings_module_missing(monkeypatch):
    """The hook's inline Python MUST import cleanly even when sentence_transformers
    is absent — the B-alpha (Jaccard) path still works."""
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    import importlib

    import lib.reinvention_semantic as rs
    importlib.reload(rs)

    # SemanticIndex (Jaccard) is stdlib-only and must remain importable.
    idx = rs.SemanticIndex()
    assert idx is not None
    # EmbeddingsIndex must raise ImportError at construction time.
    with pytest.raises(ImportError):
        rs.EmbeddingsIndex()

    # Cleanup.
    monkeypatch.delitem(sys.modules, "sentence_transformers", raising=False)
    importlib.reload(rs)
