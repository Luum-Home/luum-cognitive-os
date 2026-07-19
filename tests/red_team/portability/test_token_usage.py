# SCOPE: os-only
"""Portability proof for cos_lib/token_usage.py."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = REPO_ROOT / "cos_lib/token_usage.py"


def test_token_usage_artifact_exists() -> None:
    assert ARTIFACT.exists()


def test_imports_from_arbitrary_project_root(tmp_path: Path) -> None:
    """Falsification probe: library must not depend on OS repo cwd."""
    script = """
import importlib.util
from pathlib import Path
artifact = Path(__import__('sys').argv[1])
spec = importlib.util.spec_from_file_location('cos_token_usage_portability', artifact)
module = importlib.util.module_from_spec(spec)
__import__('sys').modules[spec.name] = module
spec.loader.exec_module(module)
item = module.normalize_usage_record({'model': 'gpt-5.1', 'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}, default_harness='codex')
assert item.provider == 'openai'
assert item.harness == 'codex'
assert item.input_tokens == 10
assert item.output_tokens == 2
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ARTIFACT)],
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
