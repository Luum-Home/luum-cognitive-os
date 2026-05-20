from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ARTIFACT = REPO_ROOT / "hooks" / "secret-audit-pre-commit.sh"

def test_secret_audit_pre_commit_safe_from_arbitrary_project_root(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    result = subprocess.run(["bash", str(ARTIFACT)], cwd=tmp_path, env=env, text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
