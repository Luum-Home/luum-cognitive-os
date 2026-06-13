from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_laptop_integration_uses_uv_managed_python_by_default() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "COS_TEST_PYTHON ?= uv run python3" in makefile
    assert "COS_TEST_PYTHON ?= python3" not in makefile
