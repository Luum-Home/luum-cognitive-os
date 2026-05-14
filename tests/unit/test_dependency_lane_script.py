from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dependency-lane.sh"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_list_lanes_includes_expected_heavy_lanes() -> None:
    result = run_script("list")

    assert result.returncode == 0, result.stderr
    lanes = set(result.stdout.splitlines())
    assert {"llm", "observability", "memory", "guardrails", "crawling", "jupyter", "semantic"} <= lanes


def test_path_returns_requirement_file() -> None:
    result = run_script("path", "observability")

    assert result.returncode == 0, result.stderr
    path = Path(result.stdout.strip())
    assert path.name == "observability.txt"
    assert path.exists()
    assert "arize-phoenix" in path.read_text()


def test_show_outputs_lane_requirements() -> None:
    result = run_script("show", "semantic")

    assert result.returncode == 0, result.stderr
    assert "sentence-transformers" in result.stdout
    assert "numpy" in result.stdout


def test_unknown_lane_fails_with_available_lanes() -> None:
    result = run_script("path", "does-not-exist")

    assert result.returncode != 0
    assert "unknown lane" in result.stderr
    assert "observability" in result.stderr


def test_audit_reports_lane_coverage_gap() -> None:
    result = run_script("audit", "semantic")

    assert result.returncode == 0, result.stderr
    assert "dependency lane audit: semantic" in result.stdout
    assert "numpy" in result.stdout or "sentence-transformers" in result.stdout
