# SCOPE: os-only
"""Portability probes for scripts/cos_coverage.py and scripts/cos-coverage shim.

These probes execute the CLI against temporary non-SO project directories to
verify the tool works portably, does not depend on repository-local runtime
state, and degrades gracefully when optional data sources are absent.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLI = REPO_ROOT / "scripts" / "cos_coverage.py"
SHIM = REPO_ROOT / "scripts" / "cos-coverage"


def run_cli(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def run_shim(project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SHIM), "--project-dir", str(project), *extra],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def write_audit_record(metrics: Path, component: str, classification: str) -> None:
    metrics.mkdir(parents=True, exist_ok=True)
    record = {
        "source": "aspirational-audit",
        "event_type": "component.classified",
        "schema_version": "1.0",
        "timestamp": "2026-05-02T12:00:00+00:00",
        "payload": {
            "component": component,
            "classification": classification,
            "signals": {},
            "reason": "portability-test",
        },
    }
    with (metrics / "aspirational-audit.jsonl").open("a") as fh:
        fh.write(json.dumps(record) + "\n")


# ── Core portability ───────────────────────────────────────────────────────────

def test_empty_non_so_project_exits_zero(tmp_path: Path) -> None:
    """Empty directory (no SO runtime state) must not crash."""
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr


def test_json_output_valid_on_empty_project(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    assert data["coverage_pct"] == 0.0


def test_brief_output_is_single_line_on_empty_project(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--brief")
    assert result.returncode == 0, result.stderr
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 1
    assert "ACC:" in result.stdout


def test_json_schema_required_keys_always_present(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--json")
    data = json.loads(result.stdout)
    for key in ("coverage_pct", "real", "dormant", "aspirational",
                "mapped", "weak_proof", "unmapped", "trend", "generated_at"):
        assert key in data, f"Missing key: {key}"


def test_counts_real_and_dormant_from_consumer_audit(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    write_audit_record(metrics, "scripts/alpha.py", "REAL")
    write_audit_record(metrics, "scripts/beta.py", "REAL")
    write_audit_record(metrics, "hooks/dormant.sh", "DORMANT")
    result = run_cli(tmp_path, "--json", "--refresh")
    data = json.loads(result.stdout)
    assert data["real"] == 2
    assert data["dormant"] == 1
    assert data["aspirational"] == 0


def test_coverage_pct_computed_correctly_for_consumer_data(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    write_audit_record(metrics, "scripts/r1.py", "REAL")   # 1
    write_audit_record(metrics, "hooks/d1.sh", "DORMANT")  # 1
    write_audit_record(metrics, "hooks/d2.sh", "DORMANT")  # 1
    # coverage = 1/3 = 33.3%
    result = run_cli(tmp_path, "--json", "--refresh")
    data = json.loads(result.stdout)
    assert abs(data["coverage_pct"] - 33.3) < 0.2


def test_no_internal_cached_at_in_json_output(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--json")
    data = json.loads(result.stdout)
    assert "_cached_at" not in data


def test_refresh_flag_accepted_without_error(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--refresh")
    assert result.returncode == 0, result.stderr


def test_shim_brief_matches_python_brief(tmp_path: Path) -> None:
    """bash shim output must match direct python3 invocation for --brief."""
    metrics = tmp_path / ".cognitive-os" / "metrics"
    write_audit_record(metrics, "scripts/x.py", "REAL")
    # Warm cache via Python
    run_cli(tmp_path, "--refresh")
    py_result = run_cli(tmp_path, "--brief")
    sh_result = run_shim(tmp_path, "--brief")
    assert sh_result.returncode == 0, sh_result.stderr
    assert py_result.stdout.strip() == sh_result.stdout.strip()


# ── Cache isolation ────────────────────────────────────────────────────────────

def test_cache_written_to_consumer_project_dir(tmp_path: Path) -> None:
    run_cli(tmp_path, "--refresh")
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    assert cache.exists(), "Cache file must be written inside the project dir, not the SO repo"


def test_two_consumer_projects_have_independent_caches(
    tmp_path: Path,
    tmp_path_factory,  # pytest TempPathFactory
) -> None:
    proj_a = tmp_path
    proj_b = tmp_path_factory.mktemp("proj_b")

    metrics_a = proj_a / ".cognitive-os" / "metrics"
    write_audit_record(metrics_a, "scripts/a1.py", "REAL")

    metrics_b = proj_b / ".cognitive-os" / "metrics"
    write_audit_record(metrics_b, "scripts/b1.py", "REAL")
    write_audit_record(metrics_b, "hooks/b2.sh", "DORMANT")

    run_cli(proj_a, "--refresh")
    run_cli(proj_b, "--refresh")

    res_a = run_cli(proj_a, "--json")
    res_b = run_cli(proj_b, "--json")
    data_a = json.loads(res_a.stdout)
    data_b = json.loads(res_b.stdout)

    assert data_a["real"] == 1
    assert data_b["real"] == 1
    assert data_b["dormant"] == 1
    assert data_a["dormant"] == 0


# ── Falsification ─────────────────────────────────────────────────────────────

def test_falsification_unknown_flag_fails(tmp_path: Path) -> None:
    result = run_cli(tmp_path, "--definitely-not-a-real-flag")
    assert result.returncode != 0


def test_falsification_corrupt_audit_does_not_crash(tmp_path: Path) -> None:
    """Corrupt JSONL lines must be skipped, not crash the CLI."""
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True, exist_ok=True)
    # Write one good and one corrupt line
    with (metrics / "aspirational-audit.jsonl").open("w") as fh:
        good = {"source": "a", "event_type": "component.classified",
                "payload": {"component": "x.py", "classification": "REAL"}}
        fh.write(json.dumps(good) + "\n")
        fh.write("NOT JSON {{{ CORRUPT\n")
    result = run_cli(tmp_path, "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["real"] == 1


def test_falsification_stale_cache_not_served_beyond_ttl(tmp_path: Path) -> None:
    """Verifies the script recomputes when cache is expired."""
    # Step 1: write cache with old timestamp
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    stale_data = {
        "_cached_at": time.time() - 120,  # 2 minutes ago (> 30s TTL)
        "coverage_pct": 99.9,
        "real": 999,
        "dormant": 0,
        "aspirational": 0,
        "on_demand": 0,
        "metadata": 0,
        "mapped": 0,
        "weak_proof": 0,
        "unmapped": 0,
        "tiers": {},
        "trend": {},
        "generated_at": "2026-01-01T00:00:00Z",
        "project": str(tmp_path),
    }
    cache.write_text(json.dumps(stale_data))

    # Step 2: run without --refresh; stale cache should be ignored
    result = run_cli(tmp_path, "--json")
    data = json.loads(result.stdout)
    # Must recompute: empty project means 0, not 99.9
    assert data["coverage_pct"] == 0.0, (
        f"Stale cache was served: got coverage_pct={data['coverage_pct']}, expected 0.0"
    )
