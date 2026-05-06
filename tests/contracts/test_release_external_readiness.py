from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "cos-release-external-readiness"


def test_release_external_readiness_reports_existing_tag_without_secret_leak(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "tag", "v9.9.9"], cwd=tmp_path, check=True)

    result = subprocess.run(
        [str(SCRIPT), "--project-dir", str(tmp_path), "--version", "v9.9.9", "--json"],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["status"] == "blocked"
    assert "tag v9.9.9 already exists locally" in payload["reasons"]
    assert "HOMEBREW_TAP_GITHUB_TOKEN" not in result.stdout
