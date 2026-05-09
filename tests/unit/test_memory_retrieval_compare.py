from __future__ import annotations

from pathlib import Path

from lib.memory_retrieval_compare import compare_reports

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "docs" / "reports" / "memory-retrieval-wave2"


def test_memory_retrieval_compare_selects_graph_path_as_smallest_passing_delta() -> None:
    comparison = compare_reports(sorted(path for path in REPORTS.glob("*.json") if not path.name.startswith("comparison-")))

    assert comparison["winner"]["strategy"] == "graph-path-local"
    assert comparison["decision"]["next_port"] == "M1+M3"
    row = next(row for row in comparison["rows"] if row["strategy"] == "graph-path-local")
    assert row["delta_passed"] == 3
    assert row["regressed_fixtures"] == []
