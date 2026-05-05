from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPAIR = ROOT / "scripts" / "cos_repair.py"
pytestmark = pytest.mark.behavior


def test_cos_repair_dry_run_reports_reversible_backup_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    result = subprocess.run(
        [sys.executable, str(REPAIR), "--repo", str(repo), "--dry-run", "--json", "--backup-root", str(tmp_path / "backups")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "dry-run"
    assert payload["repairs"]["preserved_wip_cleanup"]["mode"] == "dry-run"
    assert str(tmp_path / "backups") in payload["backup_root"]
