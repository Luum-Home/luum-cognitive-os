"""Unit tests for the auto-marker injection in tests/conftest.py (REQ-3, ADR-069).

Tests verify that ``pytest_collection_modifyitems`` correctly injects lane
markers based on test file paths, preserves existing markers, and is idempotent.

These tests call the hook logic directly (not via subprocess) to keep them
fast and free of pytester dependencies.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Import the hook under test from the root conftest.
# ---------------------------------------------------------------------------

_TESTS_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _TESTS_ROOT.parent

# The root conftest is at tests/conftest.py.  We import it via importlib to
# avoid polluting sys.modules under a misleading name.
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("_root_conftest", _TESTS_ROOT / "conftest.py")
assert _spec is not None and _spec.loader is not None
_root_conftest = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_root_conftest)  # type: ignore[union-attr]

_inject_hook = _root_conftest.pytest_collection_modifyitems
_PATH_TO_MARKER = _root_conftest._PATH_TO_MARKER


# ---------------------------------------------------------------------------
# Minimal synthetic Item — enough for the hook to inspect
# ---------------------------------------------------------------------------


class _FakeMarker:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeItem:
    """Minimal stand-in for a pytest.Item with fspath, iter_markers, and add_marker."""

    def __init__(self, fspath: Path) -> None:
        self.fspath = fspath
        self._markers: list[_FakeMarker] = []

    def iter_markers(self):
        yield from self._markers

    def add_marker(self, marker) -> None:
        # pytest.mark.<name> returns a MarkDecorator; extract the name.
        name = marker.name if hasattr(marker, "name") else str(marker)
        self._markers.append(_FakeMarker(name))

    @property
    def marker_names(self) -> set[str]:
        return {m.name for m in self._markers}


# ---------------------------------------------------------------------------
# Test 1 — item with path tests/unit/foo.py gets the ``unit`` marker
# ---------------------------------------------------------------------------


def test_unit_path_gets_unit_marker():
    """An item whose fspath is under tests/unit/ receives the ``unit`` marker."""
    if "unit" not in _PATH_TO_MARKER.values():
        pytest.skip("unit lane not configured in .cognitive-os/test-lanes.yaml")

    item = _FakeItem(fspath=_PROJECT_ROOT / "tests" / "unit" / "foo.py")
    _inject_hook(config=None, items=[item])
    assert "unit" in item.marker_names, (
        f"Expected 'unit' marker, got: {item.marker_names}"
    )


# ---------------------------------------------------------------------------
# Test 2 — item with path tests/audit/bar.py gets the ``audit`` marker
# ---------------------------------------------------------------------------


def test_audit_path_gets_audit_marker():
    """An item whose fspath is under tests/audit/ receives the ``audit`` marker."""
    if "audit" not in _PATH_TO_MARKER.values():
        pytest.skip("audit lane not configured in .cognitive-os/test-lanes.yaml")

    item = _FakeItem(fspath=_PROJECT_ROOT / "tests" / "audit" / "bar.py")
    _inject_hook(config=None, items=[item])
    assert "audit" in item.marker_names, (
        f"Expected 'audit' marker, got: {item.marker_names}"
    )


# ---------------------------------------------------------------------------
# Test 3 — existing marker ``slow`` is preserved AND the lane marker is added
# ---------------------------------------------------------------------------


def test_existing_markers_are_preserved():
    """An item with @pytest.mark.slow keeps that marker AND gains the lane marker."""
    if "unit" not in _PATH_TO_MARKER.values():
        pytest.skip("unit lane not configured in .cognitive-os/test-lanes.yaml")

    item = _FakeItem(fspath=_PROJECT_ROOT / "tests" / "unit" / "test_slow.py")
    # Pre-install a ``slow`` marker to simulate @pytest.mark.slow.
    item._markers.append(_FakeMarker("slow"))

    _inject_hook(config=None, items=[item])

    assert "slow" in item.marker_names, "Pre-existing 'slow' marker was removed"
    assert "unit" in item.marker_names, (
        f"Expected 'unit' marker to be added, got: {item.marker_names}"
    )


# ---------------------------------------------------------------------------
# Test 4 — idempotency: running the hook twice does not duplicate markers
# ---------------------------------------------------------------------------


def test_auto_marker_is_idempotent():
    """Calling the hook twice must not result in duplicate lane markers."""
    if "unit" not in _PATH_TO_MARKER.values():
        pytest.skip("unit lane not configured in .cognitive-os/test-lanes.yaml")

    item = _FakeItem(fspath=_PROJECT_ROOT / "tests" / "unit" / "test_idem.py")
    _inject_hook(config=None, items=[item])
    _inject_hook(config=None, items=[item])

    unit_count = sum(1 for m in item._markers if m.name == "unit")
    assert unit_count == 1, (
        f"Expected exactly 1 'unit' marker, got {unit_count} after two hook calls"
    )


# ---------------------------------------------------------------------------
# Test 5 — directory boundary: tests/unit_extra/ MUST NOT match tests/unit lane
# ---------------------------------------------------------------------------


def test_directory_boundary_prevents_prefix_collision():
    """A path like tests/unit_extra/foo.py must not gain the 'unit' marker.

    Regression: previous startswith() check matched 'tests/unit' as a prefix of
    'tests/unit_extra', which is wrong. The lane match must respect directory
    boundaries (exact match or prefix followed by '/').
    """
    if "unit" not in _PATH_TO_MARKER.values():
        pytest.skip("unit lane not configured in .cognitive-os/test-lanes.yaml")

    item = _FakeItem(fspath=_PROJECT_ROOT / "tests" / "unit_extra" / "foo.py")
    _inject_hook(config=None, items=[item])
    assert "unit" not in item.marker_names, (
        f"tests/unit_extra/foo.py should NOT match the 'unit' lane; "
        f"got markers: {item.marker_names}"
    )
