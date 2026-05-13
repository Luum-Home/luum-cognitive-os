# SCOPE: os-only
"""Portability probe for lib/agent_runner.py — ADR-264 envelope integration.

Falsification probe: if the envelope integration is absent, the import of
`wrap_if_large` from `lib.tool_result_envelope` will fail and this test fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_envelope_integration_present():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.tool_result_envelope import wrap_if_large, ENVELOPE_THRESHOLD\n"
        "assert callable(wrap_if_large)\n"
        "assert isinstance(ENVELOPE_THRESHOLD, int) and ENVELOPE_THRESHOLD == 28*1024\n"
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


def test_agent_runner_imports():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib import agent_runner\n"
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
