from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_conftest():
    path = Path(__file__).resolve().parents[1] / "chaos" / "conftest.py"
    spec = importlib.util.spec_from_file_location("chaos_conftest_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_snapshot_restores_modified_production_file(tmp_path: Path) -> None:
    guard = _load_conftest()
    target = tmp_path / "lib" / "example.py"
    target.parent.mkdir()
    target.write_text("original\n", encoding="utf-8")
    snapshot = guard.take_source_snapshot(tmp_path)

    target.write_text("mutated\n", encoding="utf-8")
    mutations = guard.restore_source_mutations(tmp_path, snapshot)

    assert target.read_text(encoding="utf-8") == "original\n"
    assert [(m.kind, m.path) for m in mutations] == [("modified-restored", "lib/example.py")]


def test_snapshot_removes_added_production_file(tmp_path: Path) -> None:
    guard = _load_conftest()
    (tmp_path / "scripts").mkdir()
    snapshot = guard.take_source_snapshot(tmp_path)
    added = tmp_path / "scripts" / "new-tool"
    added.write_text("boom\n", encoding="utf-8")

    mutations = guard.restore_source_mutations(tmp_path, snapshot)

    assert not added.exists()
    assert [(m.kind, m.path) for m in mutations] == [("added-removed", "scripts/new-tool")]


def test_snapshot_ignores_pycache_artifacts(tmp_path: Path) -> None:
    guard = _load_conftest()
    pycache = tmp_path / "lib" / "__pycache__"
    pycache.mkdir(parents=True)
    ignored = pycache / "example.cpython-314.pyc"
    ignored.write_bytes(b"cache")

    snapshot = guard.take_source_snapshot(tmp_path)
    mutations = guard.restore_source_mutations(tmp_path, snapshot)

    assert snapshot == {}
    assert mutations == []
    assert ignored.exists()
