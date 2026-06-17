from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import cos_epistemic_review as er

ROOT = Path(__file__).resolve().parents[2]


def run_script(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ROOT / "scripts" / "cos_epistemic_review.py"), *args],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def test_evidence_ranking_prefers_current_tests_over_self_reported_benchmark() -> None:
    ranked = er.rank_evidence([
        "self-reported benchmark says 17% tokens saved",
        "pytest command output exit 0 from source inspection",
        "ADR links the implementation path",
    ])
    assert ranked[0]["tier"] == "source-code-tests-now"
    assert ranked[-1]["tier"] == "self-reported-benchmark"


def test_claim_audit_downgrades_interested_witness_without_independent_verification(tmp_path: Path) -> None:
    result = run_script(
        tmp_path,
        "claim-audit",
        "--project-dir",
        str(tmp_path),
        "--claim",
        "our benchmark proves real savings",
        "--source",
        "self-authored benchmark report",
        "--source-interest",
        "self-authored",
        "--evidence",
        "self-reported benchmark says 17% faster",
        "--json",
    )
    assert result.returncode == 2, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["interested_witness"] is True
    assert payload["verdict"] == "needs-independent-verification"
    assert payload["confidence"] < 75
    assert (tmp_path / ".cognitive-os/epistemic-review/claim-audit.jsonl").exists()


def test_claim_audit_supports_external_claim_with_current_passing_verification(tmp_path: Path) -> None:
    result = run_script(
        tmp_path,
        "claim-audit",
        "--project-dir",
        str(tmp_path),
        "--claim",
        "tests pass now",
        "--source",
        "local test run",
        "--source-interest",
        "neutral",
        "--evidence",
        "pytest command output exit 0 from source inspection",
        "--verification-command",
        "python3 -c 'raise SystemExit(0)'",
        "--json",
    )
    assert result.returncode == 0, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "supported"
    assert payload["verification"]["passed"] is True


def test_claim_audit_failed_verification_is_unsupported(tmp_path: Path) -> None:
    result = run_script(
        tmp_path,
        "claim-audit",
        "--project-dir",
        str(tmp_path),
        "--claim",
        "tests pass now",
        "--source-interest",
        "neutral",
        "--evidence",
        "pytest command output exit 0",
        "--verification-command",
        "python3 -c 'raise SystemExit(3)'",
        "--json",
    )
    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "unsupported"
    assert payload["verification"]["returncode"] == 3


def test_benchmark_gaming_audit_flags_special_case(tmp_path: Path) -> None:
    bench = tmp_path / "src" / "optimizer.py"
    bench.parent.mkdir()
    bench.write_text(
        "def run(name):\n"
        "    if name == 'benchmark':\n"
        "        return hardcoded_benchmark_fixture()  # benchmark gaming\n"
        "    return normal_path()\n",
        encoding="utf-8",
    )
    result = run_script(tmp_path, "benchmark-gaming-audit", "--project-dir", str(tmp_path), "--path", "src", "--json")
    assert result.returncode == 2, result.stderr + result.stdout
    payload = json.loads(result.stdout)
    assert payload["verdict"] == "needs-refutation"
    assert payload["high_count"] >= 1
