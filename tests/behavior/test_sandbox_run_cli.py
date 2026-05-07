from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.behavior
def test_sandbox_run_dry_run_with_explicit_fallback(project_root: Path, tmp_path: Path) -> None:
    proc = subprocess.run(
        [str(project_root / "scripts" / "cos-sandbox-run"), "--workspace", str(tmp_path), "--allow-fallback", "--json", "--", "echo", "ok"],
        text=True,
        capture_output=True,
        check=True,
        env={"COS_SANDBOX_DISABLE_NATIVE": "1"},
    )
    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "sandbox-adapter/v1"
    assert payload["fallback_used"] is True
