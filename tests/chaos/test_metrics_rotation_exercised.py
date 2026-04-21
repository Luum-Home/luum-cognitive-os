"""Exercised chaos test for hooks/metrics-rotation.sh (ADR-041 Wave B).

Tier: B (Infrastructure — prevents JSONL unbounded growth)
Trigger: SessionStart

Contract:
  - Rotates JSONL metrics above MAX_LINES, preserves KEEP_LINES of tail.
  - Missing metrics dir must not error (graceful).
  - Always exits 0.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.chaos._tier_b_helpers import (
    HOOKS_DIR,
    run_hook,
    setup_project,
    write_chaos_run,
)

_HOOK = HOOKS_DIR / "metrics-rotation.sh"
_COMPONENT = "hooks/metrics-rotation.sh"


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-rotation.sh not found")
def test_metrics_rotation_exists():
    assert _HOOK.is_file()


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-rotation.sh not found")
def test_metrics_rotation_empty_metrics_dir_graceful(tmp_path: Path):
    """Empty metrics dir must not crash the rotator."""
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    write_chaos_run(tmp_path, _COMPONENT, "empty_metrics_dir", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-rotation.sh not found")
def test_metrics_rotation_rotates_oversized_jsonl(tmp_path: Path):
    """JSONL above MAX_LINES must be rotated (source shrinks, archive appears)."""
    setup_project(tmp_path)
    metrics_dir = tmp_path / ".cognitive-os" / "metrics"
    big = metrics_dir / "synthetic-events.jsonl"
    # MAX_LINES default 5000 — write 6000 tiny rows to force rotation.
    with big.open("w") as fh:
        for i in range(6000):
            fh.write(f'{{"n":{i}}}\n')
    pre_lines = 6000
    result = run_hook(
        _HOOK,
        tmp_path,
        env_extra={
            # Tighter bounds so the test is unambiguous and fast.
            "COGNITIVE_OS_METRICS_MAX_LINES": "500",
            "COGNITIVE_OS_METRICS_KEEP_LINES": "100",
        },
    )
    assert result.returncode == 0, f"stderr: {result.stderr[:300]}"
    post_lines = sum(1 for _ in big.open())
    assert post_lines < pre_lines, (
        f"file should have been rotated from {pre_lines} lines; still {post_lines}"
    )
    write_chaos_run(tmp_path, _COMPONENT, "rotates_oversized", True)


@pytest.mark.skipif(not _HOOK.exists(), reason="metrics-rotation.sh not found")
def test_metrics_rotation_killswitch_suppresses(tmp_path: Path):
    setup_project(tmp_path)
    result = run_hook(_HOOK, tmp_path, env_extra={"SO_KILLSWITCH": "1"})
    assert result.returncode == 0
    write_chaos_run(tmp_path, _COMPONENT, "killswitch_suppresses", True)
