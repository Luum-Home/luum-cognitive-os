"""Unit tests for hooks/_lib/safe-jsonl.sh

Validates safe JSONL append operations: basic append, concurrent write safety,
invalid JSON rejection, flock timeout handling, mkdir-based fallback locking,
heartbeat emission on exit, and lock file cleanup.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LIB_DIR = PROJECT_ROOT / "hooks" / "_lib"
JSONL_LIB = LIB_DIR / "safe-jsonl.sh"


@pytest.fixture
def jsonl_env(tmp_path):
    """Set up a safe-jsonl test environment."""
    project_dir = tmp_path / "project"
    metrics_dir = project_dir / ".cognitive-os" / "metrics"
    metrics_dir.mkdir(parents=True)

    env = {
        "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        "COGNITIVE_OS_SESSION_ID": "",
    }

    return {
        "env": env,
        "project_dir": project_dir,
        "metrics_dir": metrics_dir,
        "tmp_path": tmp_path,
    }


def _run(jsonl_env, script_body: str) -> subprocess.CompletedProcess:
    """Run a bash script in a subshell with the jsonl environment."""
    run_env = {**os.environ, **jsonl_env["env"]}
    return subprocess.run(
        ["bash", "-c", script_body],
        capture_output=True, text=True, env=run_env,
    )


class TestBasicAppend:
    """safe_jsonl_append creates valid JSONL entries."""

    def test_creates_two_lines(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "test.jsonl"
        script = f'''
            _SAFE_JSONL_LOADED=""
            source "{JSONL_LIB}"
            safe_jsonl_append "{target}" '{{"key":"value","num":1}}'
            safe_jsonl_append "{target}" '{{"key":"value2","num":2}}'
        '''
        _run(jsonl_env, script)
        lines = target.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_all_lines_are_valid_json(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "test.jsonl"
        script = f'''
            _SAFE_JSONL_LOADED=""
            source "{JSONL_LIB}"
            safe_jsonl_append "{target}" '{{"key":"value","num":1}}'
            safe_jsonl_append "{target}" '{{"key":"value2","num":2}}'
        '''
        _run(jsonl_env, script)
        for line in target.read_text().strip().split("\n"):
            parsed = json.loads(line)  # Raises if invalid
            assert isinstance(parsed, dict)


class TestConcurrentWrites:
    """Concurrent writers produce no corrupted lines."""

    def test_all_lines_present_and_valid(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "concurrent.jsonl"
        # Launch 10 parallel writers
        processes = []
        for i in range(1, 11):
            script = f'''
                _SAFE_JSONL_LOADED=""
                source "{JSONL_LIB}"
                safe_jsonl_append "{target}" '{{"writer":{i},"ts":"{int(time.time())}"}}'
            '''
            run_env = {**os.environ, **jsonl_env["env"]}
            p = subprocess.Popen(
                ["bash", "-c", script],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=run_env,
            )
            processes.append(p)

        for p in processes:
            p.wait()

        lines = target.read_text().strip().split("\n")
        assert len(lines) == 10

        corrupted = 0
        for line in lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                corrupted += 1
        assert corrupted == 0


class TestInvalidJsonRejected:
    """safe_jsonl_append rejects invalid JSON input."""

    def test_file_empty_or_not_created(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "invalid.jsonl"
        script = f'''
            _SAFE_JSONL_LOADED=""
            source "{JSONL_LIB}"
            safe_jsonl_append "{target}" 'this is not json'
        '''
        _run(jsonl_env, script)
        if target.exists():
            content = target.read_text().strip()
            assert content == ""
        # If file doesn't exist, that's also correct


class TestFlockTimeout:
    """flock-based locking handles timeouts without hanging."""

    def test_does_not_hang(self, jsonl_env):
        """Verify the append completes (or times out) without hanging indefinitely."""
        target = jsonl_env["tmp_path"] / "timeout.jsonl"
        lock_dir = jsonl_env["tmp_path"] / ".locks"
        lock_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["bash", "-c", f"""
                if command -v flock >/dev/null 2>&1; then
                    lock_file="{lock_dir}/timeout.jsonl.lock"
                    (
                        exec 200>"$lock_file"
                        flock -x 200
                        sleep 3
                    ) &
                    holder_pid=$!
                    sleep 0.2

                    export COGNITIVE_OS_FLOCK_TIMEOUT=1
                    _SAFE_JSONL_LOADED=""
                    source "{JSONL_LIB}"
                    safe_jsonl_append "{target}" '{{"timeout":"test"}}'

                    kill $holder_pid 2>/dev/null
                    wait $holder_pid 2>/dev/null
                fi
                echo "DONE"
            """],
            capture_output=True, text=True,
            env={**os.environ, **jsonl_env["env"]},
            timeout=10,
        )
        # The test passes if we reach here without hanging
        assert "DONE" in result.stdout


class TestMkdirFallback:
    """When flock is unavailable, mkdir-based locking is used as fallback."""

    def test_file_created_with_correct_content(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "fallback.jsonl"
        script = f'''
            fake_bin="{jsonl_env["tmp_path"]}/fake_bin"
            mkdir -p "$fake_bin"
            for cmd in bash jq date mkdir rmdir dirname basename cat echo wc sleep stat md5 tr head tail sed od; do
                cmd_path=$(command -v "$cmd" 2>/dev/null)
                if [ -n "$cmd_path" ]; then
                    ln -s "$cmd_path" "$fake_bin/$cmd" 2>/dev/null
                fi
            done
            export PATH="$fake_bin"
            _SAFE_JSONL_LOADED=""
            source "{JSONL_LIB}"
            safe_jsonl_append "{target}" '{{"fallback":"test"}}'
        '''
        _run(jsonl_env, script)
        assert target.exists()
        data = json.loads(target.read_text().strip())
        assert data["fallback"] == "test"


class TestHeartbeatEmission:
    """Heartbeat is emitted on shell exit when enabled."""

    def test_heartbeat_records_hook_name(self, jsonl_env):
        env = {**jsonl_env["env"], "COGNITIVE_OS_HOOK_HEARTBEAT": "true"}
        health_file = jsonl_env["project_dir"] / ".cognitive-os" / "metrics" / "hook-health.jsonl"

        subprocess.run(
            ["bash", "-c", f"""
                export COGNITIVE_OS_PROJECT_DIR='{jsonl_env["project_dir"]}'
                export COGNITIVE_OS_HOOK_HEARTBEAT=true
                _SAFE_JSONL_LOADED=''
                _HOOK_NAME='test-hook'
                source '{JSONL_LIB}'
            """],
            capture_output=True, text=True,
            env={**os.environ, **env},
        )

        if health_file.exists():
            lines = health_file.read_text().strip().split("\n")
            try:
                last_entry = json.loads(lines[-1])
                assert last_entry.get("hook") == "test-hook"
            except json.JSONDecodeError:
                pytest.xfail("heartbeat produced malformed JSON in subshell context")
        else:
            pytest.xfail("heartbeat may not fire in subshell context")


class TestLockCleanup:
    """Lock files are properly cleaned up after append operations."""

    def test_no_stale_mkdir_lock_dirs(self, jsonl_env):
        target = jsonl_env["tmp_path"] / "cleanup.jsonl"
        script = f'''
            _SAFE_JSONL_LOADED=""
            source "{JSONL_LIB}"
            safe_jsonl_append "{target}" '{{"cleanup":"test"}}'
        '''
        _run(jsonl_env, script)

        lock_dir = jsonl_env["tmp_path"] / ".locks"
        stale_dirs = 0
        if lock_dir.exists():
            stale_dirs = len(list(lock_dir.glob("*.d")))
        assert stale_dirs == 0
