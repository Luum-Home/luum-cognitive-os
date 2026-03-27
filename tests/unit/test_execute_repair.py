"""Unit tests for hooks/_lib/execute-repair.sh

Validates the repair execution library: bash syntax validity, function existence,
language detection for Go/TS/JS/Rust/Python/unknown, worktree cleanup edge cases,
concurrent repair checks, fix application with various types, and build verification.
"""
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIB_DIR = PROJECT_ROOT / "hooks" / "_lib"
REPAIR_LIB = LIB_DIR / "execute-repair.sh"
JSONL_LIB = LIB_DIR / "safe-jsonl.sh"


@pytest.fixture
def repair_env(tmp_path):
    """Set up an execute-repair test environment with a git repo."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    repair_wt = project_dir / ".cognitive-os" / "repair-wt"
    metrics_dir.mkdir(parents=True)
    repair_wt.mkdir(parents=True)

    # Initialize a git repo
    subprocess.run(
        ["git", "-C", str(project_dir), "init", "-q"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(project_dir), "commit", "--allow-empty", "-m", "init", "-q"],
        capture_output=True,
    )

    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
        "COGNITIVE_OS_CB_MAX_FAILURES": "2",
        "COGNITIVE_OS_CB_COOLDOWN": "5",
        "COGNITIVE_OS_CB_HOURLY_CAP": "10",
        "COGNITIVE_OS_PHASE": "stabilization",
    }

    preamble = (
        f'_SAFE_JSONL_LOADED=""\n'
        f'source "{JSONL_LIB}"\n'
        f'source "{REPAIR_LIB}"\n'
    )

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "preamble": preamble,
        "tmp_path": tmp_path,
    }


def _run(repair_env, script_body: str) -> subprocess.CompletedProcess:
    """Run a bash script with the repair environment."""
    full_script = repair_env["preamble"] + script_body
    run_env = {**os.environ, **repair_env["env"]}
    return subprocess.run(
        ["bash", "-c", full_script],
        capture_output=True, text=True, env=run_env,
    )


class TestValidBashSyntax:
    """execute-repair.sh is syntactically valid bash."""

    def test_syntax_check_passes(self):
        result = subprocess.run(
            ["bash", "-n", str(REPAIR_LIB)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Syntax errors: {result.stderr}"


class TestFunctionsExist:
    """All expected functions are defined after sourcing the library."""

    EXPECTED_FUNCTIONS = [
        "repair_execute_deterministic",
        "repair_execute_llm",
        "repair_cleanup_worktree",
        "repair_verify",
        "_repair_detect_language",
        "_repair_apply_fix",
        "_repair_create_worktree",
        "_repair_check_concurrent",
        "_repair_log_outcome",
        "_repair_merge_back",
    ]

    @pytest.mark.parametrize("func_name", EXPECTED_FUNCTIONS)
    def test_function_defined(self, repair_env, func_name):
        result = _run(repair_env, f'type -t "{func_name}"')
        assert result.stdout.strip() == "function", f"Function '{func_name}' not found"


class TestDetectLanguage:
    """_repair_detect_language identifies project languages by marker files."""

    @pytest.mark.parametrize("marker_file,expected_lang", [
        ("go.mod", "go"),
        ("tsconfig.json", "ts"),
        ("Cargo.toml", "rust"),
        ("pyproject.toml", "py"),
    ])
    def test_detect_by_marker(self, repair_env, marker_file, expected_lang):
        wt = repair_env["tmp_path"] / f"lang-{expected_lang}"
        wt.mkdir()
        (wt / marker_file).touch()
        result = _run(repair_env, f'_repair_detect_language "{wt}"')
        assert result.stdout.strip() == expected_lang

    def test_detect_javascript(self, repair_env):
        """JS detection requires package.json file with content."""
        wt = repair_env["tmp_path"] / "lang-js"
        wt.mkdir()
        (wt / "package.json").write_text("{}")
        result = _run(repair_env, f'_repair_detect_language "{wt}"')
        assert result.stdout.strip() == "js"

    def test_detect_unknown(self, repair_env):
        """Empty directory returns 'unknown' language."""
        wt = repair_env["tmp_path"] / "lang-unknown"
        wt.mkdir()
        result = _run(repair_env, f'_repair_detect_language "{wt}"')
        assert result.stdout.strip() == "unknown"


class TestCleanupWorktree:
    """repair_cleanup_worktree handles edge cases gracefully."""

    def test_empty_path_returns_zero(self, repair_env):
        result = _run(repair_env, 'repair_cleanup_worktree ""; exit $?')
        assert result.returncode == 0

    def test_nonexistent_dir_returns_zero(self, repair_env):
        result = _run(repair_env, 'repair_cleanup_worktree "/nonexistent/path/does-not-exist"; exit $?')
        assert result.returncode == 0


class TestConcurrentCheck:
    """_repair_check_concurrent enforces max concurrent repair limits."""

    def test_none_active_returns_zero(self, repair_env):
        result = _run(repair_env, '_repair_check_concurrent; exit $?')
        assert result.returncode == 0

    def test_at_max_returns_one(self, repair_env):
        """Returns 1 when a fake active worktree already exists."""
        result = _run(repair_env, '''
            wt_base=$(_repair_worktree_base)
            fake_wt="$wt_base/repair-fake"
            mkdir -p "$fake_wt"
            echo "gitdir: /fake/path" > "$fake_wt/.git"
            _repair_check_concurrent 2>/dev/null
            exit $?
        ''')
        assert result.returncode == 1


class TestApplyFix:
    """_repair_apply_fix validates inputs and executes fix types."""

    def test_missing_command_returns_one(self, repair_env):
        wt = repair_env["tmp_path"] / "fix-test"
        wt.mkdir()
        result = _run(repair_env, f'_repair_apply_fix "{wt}" "command" "" "" 2>/dev/null; exit $?')
        assert result.returncode == 1

    def test_missing_diff_returns_one(self, repair_env):
        wt = repair_env["tmp_path"] / "fix-test2"
        wt.mkdir()
        result = _run(repair_env, f'_repair_apply_fix "{wt}" "config_change" "" "" 2>/dev/null; exit $?')
        assert result.returncode == 1

    def test_unknown_type_returns_one(self, repair_env):
        wt = repair_env["tmp_path"] / "fix-test3"
        wt.mkdir()
        result = _run(repair_env, f'_repair_apply_fix "{wt}" "magic" "do stuff" "" 2>/dev/null; exit $?')
        assert result.returncode == 1

    def test_command_success(self, repair_env):
        """A successful command fix returns 0."""
        wt = repair_env["tmp_path"] / "fix-test4"
        wt.mkdir()
        result = _run(repair_env, f'_repair_apply_fix "{wt}" "command" "true" "" 2>/dev/null; exit $?')
        assert result.returncode == 0

    def test_command_failure(self, repair_env):
        """A failing command fix returns 1."""
        wt = repair_env["tmp_path"] / "fix-test5"
        wt.mkdir()
        result = _run(repair_env, f'_repair_apply_fix "{wt}" "command" "false" "" 2>/dev/null; exit $?')
        assert result.returncode == 1


class TestVerifyUnknownLanguage:
    """repair_verify with unknown language returns success with a message."""

    def test_returns_zero(self, repair_env):
        wt = repair_env["tmp_path"] / "verify-test"
        wt.mkdir()
        (wt / ".git").touch()
        result = _run(repair_env, f'repair_verify "{wt}" "unknown"; exit $?')
        assert result.returncode == 0

    def test_output_contains_no_build_command(self, repair_env):
        wt = repair_env["tmp_path"] / "verify-test2"
        wt.mkdir()
        (wt / ".git").touch()
        result = _run(repair_env, f'''
            repair_verify "{wt}" "unknown" 2>/dev/null
            echo "$_REPAIR_VERIFY_OUTPUT"
        ''')
        assert "No build command" in result.stdout
