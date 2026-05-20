from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ARTIFACT = REPO_ROOT / "scripts" / "install-gitleaks-trufflehog.sh"

def test_install_gitleaks_trufflehog_dry_run_from_arbitrary_project_root(tmp_path: Path) -> None:
    result = subprocess.run(["bash", str(ARTIFACT), "--dry-run"], cwd=tmp_path, text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    assert "Install with your package manager" in result.stdout
