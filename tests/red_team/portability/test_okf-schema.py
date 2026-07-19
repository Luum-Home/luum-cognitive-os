# SCOPE: os-only
"""Portability proof for scripts/okf-schema.json."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/okf-schema.json"


def test_okf_schema_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_okf_schema_is_valid_json_from_arbitrary_cwd(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: schema loads without cwd dependency."""
    monkeypatch.chdir(tmp_path)
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "$schema" in data or "type" in data or "properties" in data
