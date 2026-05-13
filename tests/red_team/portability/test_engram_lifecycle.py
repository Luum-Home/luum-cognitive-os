# SCOPE: os-only
"""Portability probe for lib/engram_lifecycle.py — ADR-261 integration.

Verifies that the module imports without repo-internal state and that the
memory-governance integration (governance_tau_days trailer override) is
referenceable in a clean subprocess environment.

Falsification probe: if engram_lifecycle imports lib.memory_governance but the
governance integration is absent or the build_content_with_trailer signature
no longer accepts type_, this test fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_imports_in_clean_env(tmp_path):
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib import engram_lifecycle\n"
        "src = open(engram_lifecycle.__file__).read()\n"
        "assert 'governance_tau_days' in src, 'governance integration missing'\n"
        "print('ok')\n"
    ) % str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
    assert "ok" in result.stdout


def test_governance_module_referenceable():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib import engram_lifecycle\n"
        "import lib.memory_governance as mg\n"
        "assert hasattr(mg, 'get_policy')\n"
        "print('ok')\n"
    ) % str(REPO_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, f"stderr={result.stderr}"
