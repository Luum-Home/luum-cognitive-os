# SCOPE: both
"""Shared helper for skills that emit documentation into the 10-category
docs/ convention (ADR-054/055).

Resolves `<project_dir>/docs/<NN-category>/` and writes a timestamped
markdown file into it. If the category dir does not exist, it is created
(the scaffolder is idempotent — re-running /project-scaffold is also fine).

Intended callers: skills/security-audit (→ 04-seguridad),
skills/rules-export (→ 08-estandares), and future writers (sdd-design →
02-arquitectura, document-feature → 05-features, etc.).

Design:
    - PURE file I/O. No LLM calls, no subprocess. Safe to test with tmp_path.
    - Filename format: `<slug>-<YYYY-MM-DD>-<HHMMSS>.md`. Keeps history
      without clobbering; projects can prune by date later.
    - ValueError on invalid category (we want failure to be loud).
    - Returns the absolute Path written so the caller can log it.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

__all__ = [
    "CATEGORY_DIR_NAMES",
    "resolve_category_dir",
    "write_doc",
    "slugify",
]


CATEGORY_DIR_NAMES = (
    "01-contexto",
    "02-arquitectura",
    "03-dominio-riesgo",
    "04-seguridad",
    "05-features",
    "06-backoffice",
    "07-investigacion",
    "08-estandares",
    "09-plan-ejecucion",
    "10-resumenes",
)


def slugify(value: str) -> str:
    """Convert an arbitrary string to a filename-safe slug.

    Lowercases, replaces any run of non-[a-z0-9] with '-', strips edges.
    """
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "report"


def resolve_category_dir(project_dir: Path, category: str) -> Path:
    """Return <project_dir>/docs/<category>/, creating it if missing.

    `category` must be one of CATEGORY_DIR_NAMES (exact match — numeric
    prefix is part of the contract per ADR-054).
    """
    if category not in CATEGORY_DIR_NAMES:
        raise ValueError(
            f"unknown category {category!r}. Must be one of: "
            f"{', '.join(CATEGORY_DIR_NAMES)}"
        )
    project_dir = Path(project_dir).expanduser().resolve()
    target = project_dir / "docs" / category
    target.mkdir(parents=True, exist_ok=True)
    return target


def write_doc(
    project_dir: Path,
    category: str,
    slug: str,
    body: str,
    *,
    timestamp: Optional[datetime] = None,
    filename: Optional[str] = None,
) -> Path:
    """Write `body` to <project>/docs/<category>/<filename>.

    If `filename` is None, one is derived: `<slug>-<YYYY-MM-DD>-<HHMMSS>.md`.
    Always overwrites — timestamped filenames make collisions unlikely, and
    explicit `filename` means the caller took responsibility.

    Returns the absolute Path that was written.
    """
    cat_dir = resolve_category_dir(project_dir, category)
    if filename is None:
        ts = timestamp or datetime.now()
        filename = f"{slugify(slug)}-{ts.strftime('%Y-%m-%d-%H%M%S')}.md"
    out = cat_dir / filename
    out.write_text(body)
    return out
