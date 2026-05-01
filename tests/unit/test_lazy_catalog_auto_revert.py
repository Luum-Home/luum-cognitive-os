"""Behavioral tests for lazy-catalog-auto-revert.sh."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "lazy-catalog-auto-revert.sh"
HOOK_NAME = "lazy-catalog-auto-revert.sh"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def run_hook(project_dir: Path, *, lazy: str = "1") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(project_dir)
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    env["COS_LAZY_CATALOG"] = lazy
    return subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, env=env, timeout=5, check=False)


def test_auto_revert_outputs_env_when_miss_rate_exceeds_threshold(tmp_path: Path) -> None:
    assert HOOK_NAME in HOOK.name
    baseline = tmp_path / "docs" / "measurements" / "lazy-catalog-baseline.json"
    baseline.parent.mkdir(parents=True)
    baseline.write_text(json.dumps({"missed_skills_rate_per_session": 0.02}), encoding="utf-8")
    now = time.time()
    rows = [
        {"ts": now, "session_id": f"s{i}", "lazy_catalog_active": True, "suspected_missed_skills": ["missing"] if i == 0 else []}
        for i in range(10)
    ]
    write_jsonl(tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl", rows)

    result = run_hook(tmp_path)

    assert result.returncode == 0
    assert "COS_LAZY_CATALOG=0" in result.stdout
    assert "Skill miss rate 0.100" in result.stderr
    assert "baseline 0.020" in result.stderr


def test_auto_revert_is_silent_when_rate_stays_within_threshold(tmp_path: Path) -> None:
    baseline = tmp_path / "docs" / "measurements" / "lazy-catalog-baseline.json"
    baseline.parent.mkdir(parents=True)
    baseline.write_text(json.dumps({"missed_skills_rate_per_session": 0.10}), encoding="utf-8")
    now = time.time()
    rows = [
        {"ts": now, "session_id": f"s{i}", "lazy_catalog_active": True, "suspected_missed_skills": ["missing"] if i == 0 else []}
        for i in range(10)
    ]
    write_jsonl(tmp_path / ".cognitive-os" / "runtime" / "skill-discovery.jsonl", rows)

    result = run_hook(tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""


def test_auto_revert_respects_explicit_lazy_catalog_opt_out(tmp_path: Path) -> None:
    result = run_hook(tmp_path, lazy="0")

    assert result.returncode == 0
    assert result.stdout.strip() == ""
    assert result.stderr.strip() == ""
