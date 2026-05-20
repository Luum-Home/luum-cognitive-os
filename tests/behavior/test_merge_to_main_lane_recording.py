from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.behavior

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "merge-to-main.sh"


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_merge_to_main_dry_run_records_recommended_and_executed_lane(tmp_path: Path) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", remote], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "clone", remote, work], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _git(work, "switch", "-c", "main")
    _git(work, "config", "user.email", "merge@example.invalid")
    _git(work, "config", "user.name", "Merge Lane Test")
    (work / "README.md").write_text("base\n", encoding="utf-8")
    _git(work, "add", "README.md")
    _git(work, "commit", "-m", "base")
    _git(work, "push", "-u", "origin", "main")
    _git(work, "switch", "-c", "session/lane")
    (work / "scripts").mkdir()
    (work / "scripts" / "runtime.py").write_text("print('runtime')\n", encoding="utf-8")
    _git(work, "add", "scripts/runtime.py")
    _git(work, "commit", "-m", "runtime change")

    result = subprocess.run(
        ["bash", str(SCRIPT), "--repo", str(work), "--dry-run", "--validate", "true"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    queue = work / ".cognitive-os" / "runtime" / "main-merge-queue.jsonl"
    rows = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["status"] == "started"
    assert rows[-1]["recommended_lane"] == "landing"
    assert rows[-1]["executed_lane"] == "landing"
    assert rows[-1]["validation_rationale"] == ["runtime script/library changes require landing lane"]
    assert rows[-1]["changed_files"] == ["scripts/runtime.py"]
