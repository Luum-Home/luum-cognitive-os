# SCOPE: os-only
"""Portability proof for scripts/cos-primitive-closure-check."""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "scripts" / "cos-primitive-closure-check"


def test_wrapper_exists_and_is_executable() -> None:
    assert ARTIFACT.exists()
    assert ARTIFACT.stat().st_mode & 0o111


def test_wrapper_is_valid_bash() -> None:
    subprocess.run(["bash", "-n", str(ARTIFACT)], cwd=ROOT, check=True)


def test_wrapper_help_runs_from_arbitrary_cwd(tmp_path: Path) -> None:
    """Falsification probe: wrapper must resolve repo root independent of cwd."""
    proc = subprocess.run([str(ARTIFACT), "--help"], cwd=tmp_path, text=True, capture_output=True, check=False)
    assert proc.returncode == 0
    assert "Atomic primitive-closure" in proc.stdout


def test_wrapper_delegates_to_python_module() -> None:
    text = ARTIFACT.read_text(encoding="utf-8")
    assert "scripts/cos_primitive_closure_check.py" in text
    assert "exec python3" in text
