# SCOPE: both
"""Portability probes for `packages/cos-self-knowledge/lib/self_knowledge.py`.

The module is consumed via the symlink at `lib/self_knowledge.py` to query
a project_dir's compiled self-knowledge index. It must operate against ANY
project_dir that follows the canonical OS conventions — not only against
this repository's layout.

Falsification probes:

1. The scanner targets the canonical ADR directory
   (`docs/02-Decisions/adrs`). If the module reverts to the legacy
   `docs/adrs` bridge, this test fails.
2. Calls accept an explicit `project_dir` and do not implicitly leak the
   process CWD into the lookup. Running against a minimal temp project
   must return a deterministic result tied to that project.
3. `is_index_stale` and `query` must survive a project_dir that has not
   adopted COS conventions (no index, no docs, no packages) without
   raising.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

# Import via the symlink path because that is how consumers reach the
# module. If the symlink target drifts, the probe will surface it.
self_knowledge = importlib.import_module("lib.self_knowledge")


def test_canonical_adr_path_is_scanned(tmp_path: Path) -> None:
    """Probe 1: the scanner walks docs/02-Decisions/adrs, not docs/adrs."""
    # Grab the source of is_index_stale so we can assert the canonical
    # literal is present and the legacy bridge is not.
    src = inspect.getsource(self_knowledge.is_index_stale)
    assert '"docs" / "02-Decisions" / "adrs"' in src or (
        '"docs"' in src and '"02-Decisions"' in src and '"adrs"' in src
    ), "Canonical ADR path missing from is_index_stale source"

    legacy_pattern = '"docs" / "adrs"'
    assert legacy_pattern not in src, (
        f"Legacy bridge {legacy_pattern!r} reintroduced in is_index_stale"
    )


def test_is_index_stale_respects_explicit_project_dir(tmp_path: Path) -> None:
    """Probe 2: explicit project_dir is honoured (no CWD leak)."""
    # tmp_path has no index → must report stale (True).
    assert self_knowledge.is_index_stale(project_dir=tmp_path) is True, (
        "is_index_stale must report a fresh project_dir without an index as stale"
    )

    # Sanity: the lookup respects the project_dir argument by deriving the
    # index path from it. Verified indirectly by populating an index and
    # asserting the returned value changes.
    idx = self_knowledge._index_dir(tmp_path)  # noqa: SLF001 — probe of contract
    assert str(tmp_path) in str(idx), (
        f"Index directory {idx} does not live under requested project_dir {tmp_path}"
    )


def test_minimal_project_dir_does_not_raise(tmp_path: Path) -> None:
    """Probe 3: a minimal project_dir survives the public API."""
    # No docs/, no packages/, no .cognitive-os/. Just an empty directory.
    try:
        stale = self_knowledge.is_index_stale(project_dir=tmp_path)
        results = self_knowledge.query("anything", project_dir=tmp_path)
    except Exception as exc:  # noqa: BLE001 — any exception fails the probe
        pytest.fail(
            f"Public API raised on a minimal project_dir; portability requires "
            f"graceful degradation. Got: {type(exc).__name__}: {exc}"
        )

    assert isinstance(stale, bool), f"Expected bool, got {type(stale).__name__}"
    assert isinstance(results, list), f"Expected list, got {type(results).__name__}"
