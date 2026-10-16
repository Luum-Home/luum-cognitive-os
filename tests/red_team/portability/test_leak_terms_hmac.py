# SCOPE: os-only
"""Portability proof for scripts/leak_terms_hmac.py."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "scripts/leak_terms_hmac.py"


def test_leak_terms_hmac_safe_invocation_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: script safe invocation must not depend on OS repo cwd."""
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(tmp_path),
        "CODEX_PROJECT_DIR": str(tmp_path),
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", ""),
    })
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--help"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode in {0, 1, 2, 12, 64, 77}, output
    assert "No such file or directory" not in output
    assert "Traceback" not in output


def test_leak_terms_hmac_without_key_errors_cleanly_and_writes_nothing(tmp_path: Path) -> None:
    """Without a key the generator must stop with exit 2, touch no file, and print no secret."""
    tracked = [
        REPO_ROOT / "tests/audit/test_no_consumer_domain_leakage.py",
        REPO_ROOT / "manifests/provenance-scan.yaml",
    ]
    before = [p.read_bytes() for p in tracked]
    terms = tmp_path / "terms.txt"
    terms.write_text("fixture-name\npath:fixture-path\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in {"COS_LEAK_HMAC_KEY", "CI"}}
    env["COS_LEAK_HMAC_KEY_FILE"] = str(tmp_path / "absent.key")
    env["COS_CONSUMER_TERMS_FILE"] = str(terms)
    result = subprocess.run(
        [sys.executable, str(ARTIFACT), "--check"],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        env=env,
        timeout=20,
        check=False,
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert "COS_LEAK_HMAC_KEY" in result.stderr
    assert "fixture-name" not in result.stdout + result.stderr
    assert [p.read_bytes() for p in tracked] == before
