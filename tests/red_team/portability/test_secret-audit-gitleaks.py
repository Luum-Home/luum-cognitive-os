from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ARTIFACT = REPO_ROOT / "scripts" / "secret-audit-gitleaks.sh"

def test_secret_audit_gitleaks_missing_tool_is_advisory(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["PATH"] = "/usr/bin:/bin"
    result = subprocess.run(["bash", str(ARTIFACT)], cwd=tmp_path, env=env, text=True, capture_output=True, timeout=20, check=False)
    assert result.returncode == 0, result.stderr
    assert '"scanner":"gitleaks"' in result.stdout
