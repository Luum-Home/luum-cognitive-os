from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "cos_so_impact_eval.py"
CONTRACT = PROJECT_ROOT / "docs" / "08-References" / "benchmarks" / "so-impact-money-format-refactor.yaml"


def load_mod():
    if "cos_so_impact_eval" in sys.modules:
        return sys.modules["cos_so_impact_eval"]
    spec = importlib.util.spec_from_file_location("cos_so_impact_eval", SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cos_so_impact_eval"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_contract_loads_and_modes_are_supported() -> None:
    mod = load_mod()
    contract = mod.load_contract(CONTRACT)
    assert contract["schema"] == mod.SCHEMA
    assert "vanilla" in contract["modes"]
    assert "full-so-minus-process-loop" in contract["modes"]
    assert set(contract["modes"]).issubset(set(mod.MODE_FLAGS))


def test_plan_reports_fixture_and_output_shape() -> None:
    mod = load_mod()
    payload = mod.plan(CONTRACT, ["vanilla", "full-so"])
    assert payload["task_id"] == "money-format-refactor"
    assert payload["fixture"].endswith("fixtures/so-impact/money-format-refactor")
    assert payload["modes"] == ["vanilla", "full-so"]
    assert "trace" in payload["output_shape"]


def test_run_eval_creates_receipts_and_correctness_first_report(tmp_path: Path) -> None:
    mod = load_mod()
    receipt = mod.run_eval(CONTRACT, tmp_path, "unit-run", ["vanilla", "full-so", "full-so-minus-graphify"], keep_capsules=False)
    out = Path(receipt.output_dir)
    assert receipt.verdict == "win"
    assert (out / "contract.yaml").exists()
    assert (out / "report.md").exists()
    assert (out / "report.json").exists()
    for mode in ["vanilla", "full-so", "full-so-minus-graphify"]:
        mode_dir = out / mode
        assert (mode_dir / "trace.jsonl").exists()
        assert (mode_dir / "usage.json").exists()
        assert (mode_dir / "diff.patch").exists()
        assert (mode_dir / "verify.json").exists()
        assert (mode_dir / "process.json").exists()
        verify = json.loads((mode_dir / "verify.json").read_text(encoding="utf-8"))
        assert verify["all_required_passed"] is True
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "SO-Wide Impact Eval" in report
    assert "Correctness" not in report  # no overclaiming section title required
    payload = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert payload["modes"]["full-so"]["metrics"]["context_lines_read"] < payload["modes"]["vanilla"]["metrics"]["context_lines_read"]
    assert payload["modes"]["full-so"]["metrics"]["false_claims"] < payload["modes"]["vanilla"]["metrics"]["false_claims"]
    assert "src/money.py" in payload["modes"]["full-so"]["metrics"]["files_touched_list"]
    assert "src/money.py" in (out / "full-so" / "diff.patch").read_text(encoding="utf-8")


def test_wrapper_plan_runs_from_repo_root() -> None:
    result = subprocess.run(
        [str(PROJECT_ROOT / "scripts" / "cos-so-impact-eval"), "plan", "--contract", str(CONTRACT), "--mode", "vanilla", "--json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["modes"] == ["vanilla"]
