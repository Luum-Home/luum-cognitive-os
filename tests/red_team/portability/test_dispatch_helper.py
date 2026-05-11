# SCOPE: both
"""Portability probe for lib/dispatch_helper.py — ADR-264 envelope integration.

Falsification probe: wrap_dispatch_tool_result must exist and apply envelope
formatting idempotently.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_wrap_dispatch_helper_present():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.dispatch_helper import wrap_dispatch_tool_result\n"
        "out = wrap_dispatch_tool_result('x' * 100, 'Bash', 'ls')\n"
        "assert out == 'x' * 100, 'small output should pass through'\n"
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


def test_envelope_idempotent_large_payload():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.dispatch_helper import wrap_dispatch_tool_result\n"
        "big = 'a' * 60000\n"
        "first = wrap_dispatch_tool_result(big, 'Bash', 'ls')\n"
        "second = wrap_dispatch_tool_result(first, 'Bash', 'ls')\n"
        "assert first == second, 'envelope must be idempotent'\n"
        "assert '[TOOL RESULT ENVELOPE]' in first\n"
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
