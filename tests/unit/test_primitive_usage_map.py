from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "primitive_usage_map.py"
spec = importlib.util.spec_from_file_location("primitive_usage_map", MODULE_PATH)
assert spec and spec.loader
primitive_usage_map = importlib.util.module_from_spec(spec)
sys.modules["primitive_usage_map"] = primitive_usage_map
spec.loader.exec_module(primitive_usage_map)


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "skills" / "runner").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / "rules").mkdir()
    (root / "tests").mkdir()
    (root / "docs").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)

    (root / "scripts" / "used_by_skill.py").write_text("print('used')\n")
    (root / "scripts" / "used_by_test.py").write_text("print('tested')\n")
    (root / "scripts" / "orphan.py").write_text("print('orphan')\n")
    (root / "skills" / "runner" / "SKILL.md").write_text(
        "---\nname: runner\ndescription: run script\n---\n\nUse `scripts/used_by_skill.py`.\n"
    )
    (root / "tests" / "test_runner.py").write_text("def test_runner(): assert 'used_by_test.py'\n")
    (root / "docs" / "note.md").write_text("Mention scripts/used_by_skill.py for docs.\n")
    (root / ".github" / "workflows" / "ci.yml").write_text("run: python3 scripts/used_by_test.py\n")
    return root


def test_usage_map_counts_skill_and_other_consumers(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    rows = primitive_usage_map.build_usage(root, "scripts")
    by_path = {row.path: row for row in rows}

    assert by_path["scripts/used_by_skill.py"].skill_consumers == 1
    assert by_path["scripts/used_by_skill.py"].consumer_families["doc"] == 1
    assert by_path["scripts/used_by_test.py"].consumer_families == {"test": 1, "workflow": 1}
    assert by_path["scripts/orphan.py"].total_consumers == 0

    summary = primitive_usage_map.summarize(rows)
    assert summary["targets"] == 3
    assert summary["without_skill_consumer"] == 2
    assert summary["without_any_consumer"] == 1


def test_usage_map_cli_writes_reports_and_can_fail_on_orphans(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), "--project-dir", str(root), "--target-family", "scripts"],
        text=True,
        capture_output=True,
        check=False,
    )
    failing = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--project-dir",
            str(root),
            "--target-family",
            "scripts",
            "--fail-orphans",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((root / "docs" / "06-Daily" / "reports" / "primitive-usage-map-latest.json").read_text())
    assert payload["summary"]["without_any_consumer"] == 1
    assert "Primitive Usage Map" in (root / "docs" / "06-Daily" / "reports" / "primitive-usage-map-latest.md").read_text()
    assert failing.returncode == 1
