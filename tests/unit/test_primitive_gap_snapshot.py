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
