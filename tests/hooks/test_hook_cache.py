"""Tests for hooks/_lib/cache.sh — SHA-256 file caching for hook scans.

Tests the cache library by invoking cache functions via subprocess (bash).
Verifies: cache miss on first run, cache hit after update, invalidation on
file change, invalidation on rules_hash change, and cache_invalidate_all.
"""

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_LIB = PROJECT_ROOT / "hooks" / "_lib" / "cache.sh"

pytestmark = [pytest.mark.behavior]


def _run_cache_script(script: str, env: dict, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run a bash snippet that sources cache.sh and executes cache commands."""
    full_script = f'source "{CACHE_LIB}"\n{script}'
    run_env = os.environ.copy()
    run_env.update(env)
    return subprocess.run(
        ["bash", "-e", "-c", full_script],
        capture_output=True,
        text=True,
        env=run_env,
        timeout=timeout,
    )


@pytest.fixture
def cache_env(tmp_path):
    """Set up a temporary project directory with a test file and cache dir."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create a test file to scan
    test_file = project_dir / "src" / "main.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("print('hello world')\n")

    # Create a mock config file (rules)
    config_file = project_dir / "config.yaml"
    config_file.write_text("rules:\n  - no_secrets\n")

    env = {"CLAUDE_PROJECT_DIR": str(project_dir)}

    return {
        "env": env,
        "project_dir": project_dir,
        "test_file": test_file,
        "config_file": config_file,
        "cache_dir": project_dir / ".cognitive-os" / "cache" / "hook-scans",
    }


class TestCacheHit:
    """cache_hit returns correct true/false based on cache state."""

    def test_miss_on_first_run(self, cache_env):
        """cache_hit returns 1 (false) when no cache entry exists."""
        result = _run_cache_script(
            f'cache_hit "{cache_env["test_file"]}" "rules123" && echo HIT || echo MISS',
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "MISS" in result.stdout

    def test_hit_after_update(self, cache_env):
        """cache_hit returns 0 (true) after cache_update with same file."""
        result = _run_cache_script(
            f"""
cache_update "{cache_env["test_file"]}" "rules123"
cache_hit "{cache_env["test_file"]}" "rules123" && echo HIT || echo MISS
""",
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "HIT" in result.stdout

    def test_miss_after_file_content_changes(self, cache_env):
        """cache_hit returns 1 (false) after the file content changes."""
        # First: update cache
        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules123"',
            cache_env["env"],
        )

        # Modify file content
        cache_env["test_file"].write_text("print('changed content')\n")

        # Now check: should be a miss
        result = _run_cache_script(
            f'cache_hit "{cache_env["test_file"]}" "rules123" && echo HIT || echo MISS',
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "MISS" in result.stdout

    def test_miss_after_rules_hash_changes(self, cache_env):
        """cache_hit returns 1 (false) when rules_hash changes (config changed)."""
        # Cache with one rules hash
        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules_v1"',
            cache_env["env"],
        )

        # Check with a different rules hash (simulates config change)
        result = _run_cache_script(
            f'cache_hit "{cache_env["test_file"]}" "rules_v2" && echo HIT || echo MISS',
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "MISS" in result.stdout

    def test_miss_for_nonexistent_file(self, cache_env):
        """cache_hit returns 1 (false) for a file that does not exist."""
        result = _run_cache_script(
            'cache_hit "/nonexistent/file.py" "rules123" && echo HIT || echo MISS',
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "MISS" in result.stdout


class TestCacheUpdate:
    """cache_update stores the file hash and creates the cache directory."""

    def test_creates_cache_directory(self, cache_env):
        """cache_update creates the cache directory automatically."""
        assert not cache_env["cache_dir"].exists()

        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules123"',
            cache_env["env"],
        )

        assert cache_env["cache_dir"].exists()
        assert cache_env["cache_dir"].is_dir()
        # Should have exactly one cache entry
        entries = list(cache_env["cache_dir"].iterdir())
        assert len(entries) == 1

    def test_update_overwrites_previous_entry(self, cache_env):
        """cache_update for the same file+rules_hash overwrites the old entry."""
        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules123"',
            cache_env["env"],
        )

        # Modify and update again
        cache_env["test_file"].write_text("modified\n")
        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules123"',
            cache_env["env"],
        )

        # Should still have exactly one entry (same cache key)
        entries = list(cache_env["cache_dir"].iterdir())
        assert len(entries) == 1

        # And the new content should be a HIT
        result = _run_cache_script(
            f'cache_hit "{cache_env["test_file"]}" "rules123" && echo HIT || echo MISS',
            cache_env["env"],
        )
        assert "HIT" in result.stdout

    def test_different_rules_hash_creates_separate_entry(self, cache_env):
        """Different rules_hash values create separate cache entries."""
        _run_cache_script(
            f"""
cache_update "{cache_env["test_file"]}" "rules_v1"
cache_update "{cache_env["test_file"]}" "rules_v2"
""",
            cache_env["env"],
        )

        entries = list(cache_env["cache_dir"].iterdir())
        assert len(entries) == 2


class TestCacheInvalidateAll:
    """cache_invalidate_all removes the entire cache directory."""

    def test_clears_everything(self, cache_env):
        """cache_invalidate_all removes all cached entries."""
        # Populate cache
        _run_cache_script(
            f"""
cache_update "{cache_env["test_file"]}" "rules_v1"
cache_update "{cache_env["test_file"]}" "rules_v2"
""",
            cache_env["env"],
        )
        assert cache_env["cache_dir"].exists()

        # Invalidate
        _run_cache_script("cache_invalidate_all", cache_env["env"])

        assert not cache_env["cache_dir"].exists()

    def test_invalidate_then_miss(self, cache_env):
        """After cache_invalidate_all, cache_hit returns miss."""
        _run_cache_script(
            f'cache_update "{cache_env["test_file"]}" "rules123"',
            cache_env["env"],
        )

        result = _run_cache_script(
            f"""
cache_invalidate_all
cache_hit "{cache_env["test_file"]}" "rules123" && echo HIT || echo MISS
""",
            cache_env["env"],
        )
        assert "MISS" in result.stdout

    def test_invalidate_noop_when_no_cache(self, cache_env):
        """cache_invalidate_all does not error when cache dir does not exist."""
        result = _run_cache_script("cache_invalidate_all", cache_env["env"])
        assert result.returncode == 0


class TestCacheDefaultRulesHash:
    """cache functions work when rules_hash is omitted (defaults to 'none')."""

    def test_default_rules_hash(self, cache_env):
        """Omitting rules_hash defaults to 'none' and still works."""
        result = _run_cache_script(
            f"""
cache_update "{cache_env["test_file"]}"
cache_hit "{cache_env["test_file"]}" && echo HIT || echo MISS
""",
            cache_env["env"],
        )
        assert result.returncode == 0
        assert "HIT" in result.stdout
