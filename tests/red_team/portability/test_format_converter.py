# SCOPE: os-only
"""Portability proof for cos_lib/format_converter.py.

Pins that ``FormatConverter`` is pure stateless string transformation with
no filesystem or cwd dependency: it must import and produce correct,
deterministic output for markdown/TSV/compact-kv/auto rendering when run
from an arbitrary working directory unrelated to the Cognitive OS repo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/format_converter.py"


def _load_module(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("portability_format_converter", ARTIFACT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_format_converter_imports_from_arbitrary_project_root(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: library import must not depend on process cwd."""
    _load_module(tmp_path, monkeypatch)


def test_format_converter_renders_real_data_from_arbitrary_cwd(tmp_path: Path, monkeypatch) -> None:
    """Falsification probe: primary entry points must produce correct output,
    not merely import cleanly, when the process cwd is nothing like the OS repo.
    """
    module = _load_module(tmp_path, monkeypatch)
    FormatConverter = module.FormatConverter

    records = [
        {"skill": "alpha", "score": 92.5, "success": True},
        {"skill": "beta", "score": 41.0, "success": False},
        {"skill": "gamma", "score": 77.3, "success": True},
        {"skill": "delta", "score": 88.8, "success": True},
    ]

    table = FormatConverter.to_markdown_table(records)
    assert table.splitlines()[0] == "| skill | score | success |"
    assert "alpha" in table and "beta" in table

    tsv = FormatConverter.to_tsv(records)
    lines = tsv.splitlines()
    assert lines[0] == "skill\tscore\tsuccess"
    assert lines[1] == "alpha\t92.5\ttrue"

    single = FormatConverter.to_compact_kv({"a": {"b": 1, "c": 2}, "d": "x"})
    assert single == "a.b=1\na.c=2\nd=x"

    # auto_format must route a >3-item uniform list to TSV in agent context
    assert FormatConverter.auto_format(records, context="agent") == tsv
    # and to a markdown table in human context
    assert FormatConverter.auto_format(records, context="human") == table
    # empty input must degrade gracefully rather than raising
    assert FormatConverter.auto_format([]) == "(no data)"
    assert FormatConverter.auto_format(None) == "(no data)"
