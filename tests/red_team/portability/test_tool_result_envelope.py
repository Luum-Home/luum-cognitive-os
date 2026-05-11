# SCOPE: both
"""Portability probe for lib/tool_result_envelope.py — ADR-264.

Behavioral probes verifying that the envelope logic is harness-agnostic:
imports cleanly without project state, threshold is the documented 28KB,
and the Markdown render format renders the canonical header.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_envelope_threshold_is_28kb():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.tool_result_envelope import ENVELOPE_THRESHOLD\n"
        "assert ENVELOPE_THRESHOLD == 28*1024, (\n"
        "    'threshold drifted: expected 28KB, got %%d' %% ENVELOPE_THRESHOLD\n"
        ")\n"
        "print('ok')\n"
    ) % str(REPO_ROOT)
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=20, check=False
    )
    assert r.returncode == 0, f"stderr={r.stderr}"


def test_passthrough_under_threshold():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.tool_result_envelope import wrap_if_large\n"
        "small = 'x' * 1024\n"
        "out = wrap_if_large(small, 'Bash', 'ls')\n"
        "assert out == small, 'under-threshold input must be returned as-is'\n"
        "print('ok')\n"
    ) % str(REPO_ROOT)
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=20, check=False
    )
    assert r.returncode == 0, f"stderr={r.stderr}"


def test_envelope_header_present_over_threshold():
    code = (
        "import sys; sys.path.insert(0, %r);\n"
        "from lib.tool_result_envelope import wrap_if_large\n"
        "big = 'a' * 60000\n"
        "out = wrap_if_large(big, 'Bash', 'ls', persist_full=False)\n"
        "assert '[TOOL RESULT ENVELOPE]' in out, 'envelope marker missing'\n"
        "assert 'full_size:' in out or 'full_chars' in out, 'envelope metadata missing'\n"
        "assert len(out) < len(big), 'envelope did not reduce payload size'\n"
        "print('ok')\n"
    ) % str(REPO_ROOT)
    r = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=20, check=False
    )
    assert r.returncode == 0, f"stderr={r.stderr}"
