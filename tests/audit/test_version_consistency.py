"""Audit package version against the latest released CHANGELOG heading."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.audit

REPO_ROOT = Path(__file__).resolve().parents[2]


def _pyproject_version() -> str:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    assert match, "pyproject.toml must declare a package version"
    return match.group(1)


def _latest_changelog_release() -> str:
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for line in text.splitlines():
        match = re.match(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", line)
        if match:
            return match.group(1)
    raise AssertionError("CHANGELOG.md must contain at least one released version heading")


def test_pyproject_version_matches_latest_changelog_release() -> None:
    assert _pyproject_version() == _latest_changelog_release()
