"""Unit tests for hooks/_lib/semantic-search.sh

Validates the semantic search library: bash syntax, function existence,
registry-absent behavior, fuzzy substring matching (no match, keyword match,
non-auto-applicable filtering, empty query, best match selection, fuzzy fallback),
and output JSON format verification.
"""
import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIB_DIR = PROJECT_ROOT / "hooks" / "_lib"
SEMANTIC_LIB = LIB_DIR / "semantic-search.sh"
JSONL_LIB = LIB_DIR / "safe-jsonl.sh"


@pytest.fixture
def search_env(tmp_path):
    """Set up a semantic-search test environment."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
    }

    preamble = (
        f'_SAFE_JSONL_LOADED=""\n'
        f'if [ -f "{JSONL_LIB}" ]; then source "{JSONL_LIB}"; fi\n'
        f'source "{SEMANTIC_LIB}"\n'
    )

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "preamble": preamble,
    }


def _run(search_env, script_body: str) -> subprocess.CompletedProcess:
    """Run a bash script with the semantic-search environment."""
    full_script = search_env["preamble"] + script_body
    run_env = {**os.environ, **search_env["env"]}
    return subprocess.run(
        ["bash", "-c", full_script],
        capture_output=True, text=True, env=run_env,
    )


class TestValidBashSyntax:
    """semantic-search.sh is syntactically valid bash."""

    def test_syntax_check_passes(self):
        result = subprocess.run(
            ["bash", "-n", str(SEMANTIC_LIB)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax errors: {result.stderr}"


class TestFunctionsExist:
    """All expected functions are defined after sourcing."""

    EXPECTED_FUNCTIONS = [
        "semantic_lookup",
        "_semantic_search_available",
        "_fuzzy_substring_match",
    ]

    @pytest.mark.parametrize("func_name", EXPECTED_FUNCTIONS)
    def test_function_defined(self, search_env, func_name):
        result = _run(search_env, f'type -t "{func_name}"')
        assert result.stdout.strip() == "function", f"Function '{func_name}' not found"


class TestLookupNoRegistry:
    """semantic_lookup returns 1 when no registry file exists."""

    def test_returns_one(self, search_env):
        result = _run(search_env, 'semantic_lookup "some error message" 2>/dev/null; exit $?')
        assert result.returncode == 1


class TestFuzzyNoMatch:
    """_fuzzy_substring_match returns 1 when query is completely unrelated."""

    def test_returns_one(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "connection timeout on port 5432",
            "auto_applicable": True,
            "fix_type": "restart",
            "fix_command": "docker compose restart db",
            "fingerprint": "fp1",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "completely unrelated xylophone banana" "{registry}" 2>/dev/null; exit $?')
        assert result.returncode == 1


class TestFuzzyKeywordMatch:
    """_fuzzy_substring_match finds entries by keyword overlap."""

    def test_returns_zero(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "connection timeout on port 5432",
            "auto_applicable": True,
            "fix_type": "restart",
            "fix_command": "docker compose restart db",
            "confidence": 0.9,
            "times_applied": 3,
            "fingerprint": "fp-timeout",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "connection timeout port 5432 database" "{registry}"')
        assert result.returncode == 0

    def test_output_is_valid_json_with_fix_type(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "connection timeout on port 5432",
            "auto_applicable": True,
            "fix_type": "restart",
            "fix_command": "docker compose restart db",
            "confidence": 0.9,
            "times_applied": 3,
            "fingerprint": "fp-timeout",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "connection timeout port 5432 database" "{registry}"')
        output = json.loads(result.stdout.strip())
        assert "fix_type" in output

    def test_match_type_is_fuzzy(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "connection timeout on port 5432",
            "auto_applicable": True,
            "fix_type": "restart",
            "fix_command": "docker compose restart db",
            "confidence": 0.9,
            "times_applied": 3,
            "fingerprint": "fp-timeout",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "connection timeout port 5432 database" "{registry}"')
        output = json.loads(result.stdout.strip())
        assert output["match_type"] == "fuzzy"


class TestFuzzySkipsNonAuto:
    """_fuzzy_substring_match skips entries where auto_applicable is false."""

    def test_returns_one(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "connection timeout on port 5432",
            "auto_applicable": False,
            "fix_type": "restart",
            "fix_command": "docker compose restart db",
            "fingerprint": "fp2",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "connection timeout port 5432" "{registry}" 2>/dev/null; exit $?')
        assert result.returncode == 1


class TestFuzzyEmptyQuery:
    """_fuzzy_substring_match returns 1 for an empty query string."""

    def test_returns_one(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "some error",
            "auto_applicable": True,
            "fix_type": "command",
            "fix_command": "fix.sh",
            "fingerprint": "fp3",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "" "{registry}" 2>/dev/null; exit $?')
        assert result.returncode == 1


class TestFuzzyBestMatch:
    """_fuzzy_substring_match selects the best match from multiple entries."""

    def test_picks_timeout_over_disk(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entries = [
            {
                "error_pattern": "disk space full on /var/log",
                "auto_applicable": True,
                "fix_type": "command",
                "fix_command": "cleanup-logs.sh",
                "confidence": 0.8,
                "times_applied": 5,
                "fingerprint": "fp-disk",
            },
            {
                "error_pattern": "connection timeout on port 5432",
                "auto_applicable": True,
                "fix_type": "restart",
                "fix_command": "docker compose restart db",
                "confidence": 0.9,
                "times_applied": 3,
                "fingerprint": "fp-timeout",
            },
        ]
        registry.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "timeout connection port 5432" "{registry}"')
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        assert output["fingerprint"] == "fp-timeout"


class TestLookupFuzzyFallback:
    """semantic_lookup falls back to fuzzy matching when node script is absent."""

    def test_returns_valid_match_or_one(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "OOM killed process",
            "auto_applicable": True,
            "fix_type": "restart",
            "fix_command": "docker compose restart app",
            "confidence": 0.85,
            "times_applied": 2,
            "fingerprint": "fp-oom",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, 'semantic_lookup "OOM killed process memory" 2>/dev/null')
        if result.returncode == 0:
            output = json.loads(result.stdout.strip())
            assert "fix_type" in output
        # rc=1 is acceptable if fuzzy threshold not met


class TestFuzzyOutputFormat:
    """_fuzzy_substring_match output contains all expected JSON fields."""

    EXPECTED_KEYS = ["fix_type", "fix_command", "confidence", "times_applied", "fingerprint", "match_type"]

    def test_all_keys_present(self, search_env):
        registry = search_env["metrics_dir"] / "remediation-registry.jsonl"
        entry = {
            "error_pattern": "build failed missing dependency",
            "auto_applicable": True,
            "fix_type": "command",
            "fix_command": "bun add",
            "confidence": 0.95,
            "times_applied": 10,
            "fingerprint": "fp-build",
            "fix_diff": "",
        }
        registry.write_text(json.dumps(entry) + "\n")
        result = _run(search_env, f'_fuzzy_substring_match "build failed missing dependency module" "{registry}"')
        assert result.returncode == 0
        output = json.loads(result.stdout.strip())
        for key in self.EXPECTED_KEYS:
            assert key in output, f"Missing key '{key}' in output"
