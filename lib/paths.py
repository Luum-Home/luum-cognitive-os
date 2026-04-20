# SCOPE: both
"""Canonical project-root resolver for the luum-agent-os kernel.

Implements **Pattern A** — the dominant resolution strategy used at 10 sites
across the codebase (as catalogued in the characterisation tests).

Pattern A semantics::

    CLAUDE_PROJECT_DIR  →  COGNITIVE_OS_PROJECT_DIR  →  None (not configured)

``CLAUDE_PROJECT_DIR`` wins when non-empty; ``COGNITIVE_OS_PROJECT_DIR`` is the
fallback; both absent (or empty) yields ``None`` which callers treat as
"no project dir configured".

Canonical spec: ``tests/unit/test_project_dir_resolution.py`` — the Pattern A
section defines the expected behaviour.  ``TestLibPathsProjectRoot`` (added in
Lote-3, R1) mirrors those assertions directly against this module.

**Do NOT** use this helper for:
- Pattern A' (model_router:321 — ``"."`` default, not ``None``/``""``).
- Pattern C  (dispatch_gate_check:22, queue_drainer:316 — CLAUDE only, ``"."``).
- Pattern D  (telemetry._project_root — reversed COGNITIVE_OS-first order).

Those sites intentionally differ from Pattern A and must NOT be migrated.
See ``tests/unit/test_project_dir_resolution.py`` for the rationale.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

__all__ = ["project_root"]


def project_root() -> Optional[Path]:
    """Return the project root as a :class:`pathlib.Path`, or ``None``.

    Precedence (Pattern A, canonical for 10 call-sites):

    1. ``CLAUDE_PROJECT_DIR`` env var, when non-empty.
    2. ``COGNITIVE_OS_PROJECT_DIR`` env var, when non-empty.
    3. ``None`` — both env vars absent or empty.  Callers gate on truthiness
       (``if project_dir:``) so ``None`` correctly signals "not configured"
       without raising.

    Returns
    -------
    pathlib.Path | None
        Resolved project root, or ``None`` when both env vars are absent or
        empty (matches Pattern A's ``or ""`` falsy default at the 10 sites).
    """
    raw: str = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get(
        "COGNITIVE_OS_PROJECT_DIR", ""
    )
    if not raw:
        return None
    return Path(raw)
