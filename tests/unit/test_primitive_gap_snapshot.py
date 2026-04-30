from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_gap_snapshot.py"
spec = importlib.util.spec_from_file_location("primitive_gap_snapshot", MODULE_PATH)
assert spec and spec.loader
primitive_gap_snapshot = importlib.util.module_from_spec(spec)
sys.modules["primitive_gap_snapshot"] = primitive_gap_snapshot
spec.loader.exec_module(primitive_gap_snapshot)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_collect_reports_hook_wiring_and_metrics(tmp_path: Path) -> None:
    write(tmp_path / "hooks/example.sh", "#!/usr/bin/env bash\necho ok\n")
    write(tmp_path / ".claude/settings.json", '{"command":"hooks/example.sh"}')
    write(tmp_path / "tests/test_example.py", "def test_example():\n    assert 'example.sh'\n")
    write(tmp_path / "skills/demo/SKILL.md", "---\nname: demo\n---\n")
    write(tmp_path / "rules/demo.md", "<!-- TIER: 1 -->\n# Demo\n")
    write(tmp_path / ".cognitive-os/metrics/example.jsonl", '{"event":"x"}\n')
    write(tmp_path / ".cognitive-os/metrics/empty.jsonl", "")
    write(tmp_path / ".cognitive-os/metrics/hook-timing.jsonl", '{"duration_ms": 10}\n{"duration_ms": 30}\n')
    write(tmp_path / "docs/adrs/ADR-001-demo.md", "# ADR-001\n")
    write(tmp_path / "docs/index.md", "ADR-001\n")
    write(tmp_path / "cognitive-os.yaml", "project:\n  phase: reconstruction\n")

    snapshot = primitive_gap_snapshot.collect(tmp_path)
    families = {family.family: family for family in snapshot.families}

    assert families["hooks"].total == 1
    assert families["hooks"].proven_signal == 1
    assert families["metrics"].total == 3
    assert families["metrics"].proven_signal == 2
    assert snapshot.hook_latency["p50_ms"] == 20
    assert snapshot.hook_latency["p95_ms"] == 30


def test_render_markdown_contains_family_summary(tmp_path: Path) -> None:
    write(tmp_path / "hooks/example.sh", "#!/usr/bin/env bash\n")
    snapshot = primitive_gap_snapshot.collect(tmp_path)

    markdown = primitive_gap_snapshot.render_markdown(snapshot)

    assert "# Primitive Gap Snapshot" in markdown
    assert "| hooks |" in markdown
    assert "Overall risk" in markdown


def test_cli_writes_trend_and_markdown(tmp_path: Path, monkeypatch) -> None:
    write(tmp_path / "hooks/example.sh", "#!/usr/bin/env bash\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "primitive_gap_snapshot.py",
            "--project-root",
            str(tmp_path),
            "--trend",
            "--markdown",
            "docs/reports/snapshot.md",
        ],
    )

    exit_code = primitive_gap_snapshot.main()

    assert exit_code == 0
    assert (tmp_path / ".cognitive-os/metrics/primitive-gap-snapshot.jsonl").exists()
    assert (tmp_path / "docs/reports/snapshot.md").exists()


def test_compare_regressions_detects_unproven_growth() -> None:
    previous = {
        "overall_risk": "medium",
        "families": [
            {"family": "hooks", "total": 10, "proven_signal": 6, "aspirational_signal": 1, "severity": "medium"}
        ],
        "hook_latency": {"p95_ms": 100},
    }
    current = {
        "overall_risk": "high",
        "families": [
            {"family": "hooks", "total": 12, "proven_signal": 6, "aspirational_signal": 2, "severity": "high"}
        ],
        "hook_latency": {"p95_ms": 800},
    }

    regressions = primitive_gap_snapshot.compare_regressions(previous, current, latency_regression_ms=500)

    assert "overall risk worsened: medium -> high" in regressions
    assert "hooks: severity worsened medium -> high" in regressions
    assert "hooks: aspirational signal increased 1 -> 2" in regressions
    assert "hooks: unproven surface grew 4 -> 6" in regressions
    assert "hook latency p95 regressed by >500ms: 100ms -> 800ms" in regressions


def test_cli_fails_on_regression_against_trend(tmp_path: Path, monkeypatch) -> None:
    write(tmp_path / "hooks/example.sh", "#!/usr/bin/env bash\n")
    previous = {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "overall_risk": "low",
        "families": [
            {"family": "hooks", "total": 0, "proven_signal": 0, "aspirational_signal": 0, "severity": "low"}
        ],
        "hook_latency": {"p95_ms": 0},
    }
    write(tmp_path / "docs/reports/history.jsonl", primitive_gap_snapshot.json.dumps(previous) + "\n")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "primitive_gap_snapshot.py",
            "--project-root",
            str(tmp_path),
            "--trend-path",
            "docs/reports/history.jsonl",
            "--fail-on-regression",
            "--regression-report",
            "docs/reports/regressions.md",
            "--markdown",
            "docs/reports/snapshot.md",
        ],
    )

    exit_code = primitive_gap_snapshot.main()

    assert exit_code == 1
    assert "Regressions" in (tmp_path / "docs/reports/regressions.md").read_text(encoding="utf-8")


def test_generated_snapshot_reports_do_not_influence_evidence_counts(tmp_path: Path) -> None:
    write(tmp_path / "docs/reports/primitive-gap-latest.json", '{"family":"mcp_tools"}\n')
    write(tmp_path / "docs/reports/primitive-gap-latest.md", "mcp_tools\n")
    write(tmp_path / "docs/reports/primitive-gap-regressions.md", "mcp regression\n")
    write(tmp_path / "docs/reports/ordinary.md", "mcp\n")

    files = primitive_gap_snapshot.text_files(tmp_path, ["docs"])
    names = {path.name for path in files}

    assert "ordinary.md" in names
    assert "primitive-gap-latest.json" not in names
    assert "primitive-gap-latest.md" not in names
    assert "primitive-gap-regressions.md" not in names
