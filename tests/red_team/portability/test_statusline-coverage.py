# SCOPE: both
"""Portability probes for scripts/statusline-coverage.sh.

Verifies the statusline segment works portably against non-SO project
directories, reads from cache only, and degrades gracefully when the
cache is absent or stale.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUSLINE = REPO_ROOT / "scripts" / "statusline-coverage.sh"
CLI_PY = REPO_ROOT / "scripts" / "cos_coverage.py"


def run_statusline(project: Path, env_overrides: dict | None = None) -> subprocess.CompletedProcess[str]:
    import os
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(STATUSLINE)],
        text=True,
        capture_output=True,
        timeout=10,
        env=env,
        check=False,
    )


def warm_cache(project: Path) -> None:
    subprocess.run(
        [sys.executable, str(CLI_PY), "--project-dir", str(project), "--refresh"],
        capture_output=True,
        timeout=15,
    )


def test_exits_zero_when_no_cache(tmp_path: Path) -> None:
    result = run_statusline(tmp_path)
    assert result.returncode == 0, result.stderr


def test_shows_stale_hint_when_no_cache(tmp_path: Path) -> None:
    result = run_statusline(tmp_path)
    assert "ACC: ?" in result.stdout
    assert "cos-coverage" in result.stdout


def test_shows_coverage_pct_when_cache_fresh(tmp_path: Path) -> None:
    warm_cache(tmp_path)
    result = run_statusline(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "ACC:" in result.stdout
    assert "%" in result.stdout
    assert "REAL:" in result.stdout
    assert "DORM:" in result.stdout


def test_output_is_single_line(tmp_path: Path) -> None:
    warm_cache(tmp_path)
    result = run_statusline(tmp_path)
    lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
    assert len(lines) == 1


def test_shows_stale_hint_when_cache_expired(tmp_path: Path) -> None:
    """When cache _cached_at is older than COS_COVERAGE_STALE_MAX, show hint."""
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    stale = {
        "_cached_at": time.time() - 400,  # 400s ago > default 300s
        "coverage_pct": 55.5,
        "real": 100,
        "dormant": 50,
        "aspirational": 30,
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
    cache.write_text(json.dumps(stale))
    result = run_statusline(tmp_path)
    assert "ACC: ?" in result.stdout


def test_stale_max_env_var_overrides_default(tmp_path: Path) -> None:
    """COS_COVERAGE_STALE_MAX=10 means anything older than 10s is stale."""
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    slightly_old = {
        "_cached_at": time.time() - 30,  # 30s ago > 10s threshold
        "coverage_pct": 55.5,
        "real": 100,
        "dormant": 50,
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
    cache.write_text(json.dumps(slightly_old))
    result = run_statusline(tmp_path, env_overrides={"COS_COVERAGE_STALE_MAX": "10"})
    # 30s old > 10s threshold -> stale
    assert "ACC: ?" in result.stdout


def test_cache_in_consumer_project_dir_not_so_repo(tmp_path: Path) -> None:
    """Statusline must read from the consumer project's cache, not SO repo cache."""
    # Write a cache with a distinctive value in tmp_path
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    distinctive = {
        "_cached_at": time.time(),
        "coverage_pct": 42.0,
        "real": 42,
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
    cache.write_text(json.dumps(distinctive))
    result = run_statusline(tmp_path)
    assert "42" in result.stdout, (
        f"Expected distinctive value 42 in output; got: {result.stdout!r}"
    )


def test_falsification_corrupt_cache_shows_hint(tmp_path: Path) -> None:
    """A corrupt cache file must produce the stale hint, not crash."""
    cache = tmp_path / ".cognitive-os" / "runtime" / "coverage-snapshot.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text("NOT VALID JSON {{{")
    result = run_statusline(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "ACC: ?" in result.stdout
