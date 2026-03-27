"""Unit tests for tests/utils/parse_repo_url.py

Validates the parse_repo_url function: full GitHub URLs, .git suffix stripping,
no-protocol handling, shorthand owner/repo format, extra path segments,
empty input rejection, and non-GitHub URL rejection.
"""
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Ensure tests/utils is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from utils.parse_repo_url import parse_repo_url


class TestFullGitHubUrl:
    """parse_repo_url extracts owner/repo from a full GitHub URL."""

    def test_extracts_owner_repo(self):
        result = parse_repo_url("https://github.com/owner/repo")
        assert result == "owner/repo"


class TestGitSuffix:
    """parse_repo_url strips the .git suffix."""

    def test_strips_dot_git(self):
        result = parse_repo_url("https://github.com/owner/repo.git")
        assert result == "owner/repo"


class TestNoProtocol:
    """parse_repo_url handles URLs without a protocol prefix."""

    def test_handles_no_protocol(self):
        result = parse_repo_url("github.com/owner/repo")
        assert result == "owner/repo"


class TestShorthand:
    """parse_repo_url accepts shorthand owner/repo format."""

    def test_shorthand_format(self):
        result = parse_repo_url("owner/repo")
        assert result == "owner/repo"


class TestExtraPath:
    """parse_repo_url strips extra path segments beyond owner/repo."""

    def test_strips_extra_segments(self):
        result = parse_repo_url("https://github.com/owner/repo/tree/main")
        assert result == "owner/repo"


class TestEmptyInput:
    """parse_repo_url raises ValueError for empty input."""

    def test_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_repo_url("")


class TestNonGitHubUrl:
    """parse_repo_url raises ValueError for non-GitHub URLs."""

    def test_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_repo_url("https://gitlab.com/owner/repo")
