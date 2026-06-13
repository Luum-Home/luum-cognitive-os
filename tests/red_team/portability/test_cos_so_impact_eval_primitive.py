# SCOPE: os-only
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = ROOT / "docs" / "08-References" / "benchmarks" / "so-impact-money-format-refactor.yaml"


def test_wrapper_exists_and_is_valid_bash() -> None:
    wrapper = ROOT / "scripts" / "cos-so-impact-eval"
    assert wrapper.exists()
    assert wrapper.stat().st_mode & 0o111
    subprocess.run(["bash", "-n", str(wrapper)], cwd=ROOT, check=True)


def test_so_impact_eval_runs_from_arbitrary_cwd(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    out = tmp_path / "evals"
    result = subprocess.run(
        [
            str(ROOT / "scripts" / "cos-so-impact-eval"),
            "run",
            "--contract",
            str(CONTRACT),
            "--output-root",
            str(out),
            "--run-id",
            "portable",
            "--mode",
            "vanilla",
            "--mode",
            "full-so",
            "--json",
        ],
        cwd=outside,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "win"
    bundle = out / "money-format-refactor" / "portable"
    assert (bundle / "contract.yaml").exists()
    assert (bundle / "full-so" / "diff.patch").exists()
    assert (bundle / "vanilla" / "trace.jsonl").exists()
