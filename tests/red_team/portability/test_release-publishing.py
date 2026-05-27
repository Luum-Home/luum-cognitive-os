# SCOPE: os-only
"""Portability proof for rules/release-publishing.md."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RULE = REPO_ROOT / "rules" / "release-publishing.md"
SCRIPT = REPO_ROOT / "scripts" / "cos-patch-release"


def test_release_publishing_rule_never_direct_main_pushes_in_publish_plan(tmp_path: Path) -> None:
    rule = RULE.read_text(encoding="utf-8")
    assert "never push directly to `main`" in rule
    result = subprocess.run(
        [str(SCRIPT), "--project-dir", str(tmp_path), "publish", "--version", "9.9.9", "--dry-run"],
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    steps = "\n".join(payload["publish"]["steps"])
    assert "git push origin main" not in steps
    assert "scripts/merge-to-main.sh" in steps
