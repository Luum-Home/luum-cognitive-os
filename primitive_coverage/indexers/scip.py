from __future__ import annotations

from pathlib import Path


def import_scip(root: Path, index_path: Path | None = None) -> dict:
    """Optional SCIP importer placeholder for future precise references."""
    candidate = index_path or root / "index.scip"
    return {"available": candidate.exists(), "path": str(candidate), "symbols": []}
