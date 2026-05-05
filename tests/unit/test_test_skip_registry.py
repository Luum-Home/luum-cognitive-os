from __future__ import annotations

import json
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "test_skip_registry.py"


def write_junit(path: Path, message: str) -> None:
    path.write_text(
        f'''<?xml version="1.0" encoding="utf-8"?>
<testsuite tests="1" skipped="1">
  <testcase classname="tests.system.test_docker" name="test_stack">
    <skipped message="{message}" />
  </testcase>
</testsuite>
''',
        encoding="utf-8",
    )


def test_skip_registry_classifies_expected_dependency_skip(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    out = tmp_path / "skip-summary.json"
    write_junit(junit, "Docker daemon not running")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--lane", "system", "--junit", str(junit), "--json-out", str(out), "--fail-unknown"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(out.read_text())
    assert payload["unknown_count"] == 0
    assert payload["counts_by_category"]["external-dependency"] == 1


def test_skip_registry_fails_unknown_skip_when_enforced(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    write_junit(junit, "temporarily skipped because this is hard")

    result = subprocess.run(
        ["python3", str(SCRIPT), "--lane", "unit", "--junit", str(junit), "--fail-unknown"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert '"unknown_count": 1' in result.stdout
