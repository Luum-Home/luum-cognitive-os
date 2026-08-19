# SCOPE: os-only
"""Paired portability proof for scripts/audit_skill_telemetry_names.py.

Falsification probes:

1. cwd-invariance — the artifact resolves its repo root from ``__file__``, never
   from the process cwd. Run from a foreign cwd it must produce byte-identical
   output. An artifact anchored on ``Path.cwd()`` fails here instead of silently
   auditing the wrong tree in a consumer checkout.
2. Verdict is derived, not hardcoded — pointed at a synthetic root whose stream
   only names skills that exist, it must exit 0; add one row naming a skill that
   does not exist and it must exit 1. An audit that always reports "clean" (or
   always reports findings) fails one of the two halves.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/audit_skill_telemetry_names.py"


def _run(cwd: Path, *args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(ARTIFACT), *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _synthetic_root(base: Path, skills: list[str], rows: list[dict]) -> Path:
    root = base / "synthetic"
    (root / ".cognitive-os" / "metrics").mkdir(parents=True, exist_ok=True)
    for name in skills:
        skill_dir = root / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(f"# {name}\n")
    stream = root / ".cognitive-os" / "metrics" / "skill-feedback.jsonl"
    stream.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return root


def test_help_succeeds_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = _run(tmp_path, "--help")
    assert result.returncode == 0, result.stderr or result.stdout
    assert "usage" in result.stdout.lower(), result.stdout


def test_runs_from_arbitrary_project_root(tmp_path: Path) -> None:
    from_repo = _run(REPO_ROOT, "--json")
    from_foreign = _run(tmp_path, "--json")
    assert from_foreign.returncode == from_repo.returncode, from_foreign.stderr
    assert from_foreign.stdout == from_repo.stdout
    assert str(tmp_path) not in from_foreign.stdout


def test_clean_stream_exits_zero(tmp_path: Path) -> None:
    root = _synthetic_root(
        tmp_path,
        ["a-real-skill"],
        [{"timestamp": "2026-01-01T00:00:00Z", "skill": "a-real-skill", "success": True}],
    )
    result = _run(tmp_path, "--root", str(root))
    assert result.returncode == 0, result.stdout + result.stderr


def test_one_unattributable_row_exits_one(tmp_path: Path) -> None:
    root = _synthetic_root(
        tmp_path,
        ["a-real-skill"],
        [
            {"timestamp": "2026-01-01T00:00:00Z", "skill": "a-real-skill", "success": True},
            {"timestamp": "2026-01-02T00:00:00Z", "skill": "not-a-skill", "success": False},
        ],
    )
    result = _run(tmp_path, "--root", str(root), "--json")
    assert result.returncode == 1, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    feedback = next(s for s in payload["streams"] if s["path"].endswith("skill-feedback.jsonl"))
    assert feedback["unattributable"] == 1
    assert feedback["valid"] == 1
    assert feedback["unattributable_names"] == {"not-a-skill": 1}


def test_sentinel_is_not_counted_as_a_finding(tmp_path: Path) -> None:
    """`unknown-agent` is skill-tracker.sh's deliberate non-attribution marker."""
    root = _synthetic_root(
        tmp_path,
        ["a-real-skill"],
        [{"timestamp": "2026-01-01T00:00:00Z", "skill": "unknown-agent", "success": True}],
    )
    result = _run(tmp_path, "--root", str(root), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    feedback = next(s for s in payload["streams"] if s["path"].endswith("skill-feedback.jsonl"))
    assert feedback["sentinel"] == 1
    assert feedback["unattributable"] == 0
