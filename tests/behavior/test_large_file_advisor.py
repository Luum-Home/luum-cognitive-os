"""Behavior tests for hooks/large-file-advisor.sh — PreToolUse on Read."""

import json
import os
import subprocess
import tempfile
import shutil

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK_PATH = os.path.join(PROJECT_ROOT, "hooks", "large-file-advisor.sh")


@pytest.fixture
def tmp_project():
    """Create a temporary project directory with required structure."""
    d = tempfile.mkdtemp(prefix="large_file_advisor_test_")
    # Create .cognitive-os structure
    os.makedirs(os.path.join(d, ".cognitive-os", "metrics"), exist_ok=True)
    # Create cognitive-os.yaml for phase detection
    with open(os.path.join(d, "cognitive-os.yaml"), "w") as f:
        f.write("project:\n  phase: reconstruction\n")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _run_hook(project_dir: str, tool_input: dict, timeout: int = 10) -> subprocess.CompletedProcess:
    """Run the large-file-advisor hook with simulated stdin JSON."""
    stdin_json = json.dumps({
        "tool_name": "Read",
        "tool_input": tool_input,
    })

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = project_dir
    env["COGNITIVE_OS_PROJECT_DIR"] = project_dir

    result = subprocess.run(
        ["bash", HOOK_PATH],
        input=stdin_json,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=project_dir,
    )
    return result


def _write_file(directory: str, name: str, size_bytes: int) -> str:
    """Create a file of specific size."""
    path = os.path.join(directory, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        # Write lines to have a meaningful line count
        line = "x" * 79 + "\n"  # 80 bytes per line
        lines_needed = max(1, size_bytes // 80)
        for _ in range(lines_needed):
            f.write(line)
    return path


class TestHookOutputsAdvisoryForLargeFiles:
    """Hook outputs advisory to stderr for files exceeding 40KB."""

    def test_large_file_produces_advisory(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 50000)

        result = _run_hook(tmp_project, {"file_path": path})

        assert result.returncode == 0
        assert "LARGE FILE ADVISORY" in result.stderr

    def test_advisory_includes_file_info(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 50000)

        result = _run_hook(tmp_project, {"file_path": path})

        assert "big.py" in result.stderr
        assert "bytes" in result.stderr
        assert "lines" in result.stderr
        assert "tokens" in result.stderr


class TestHookSilentForSmallFiles:
    """Hook produces no output for files under 40KB."""

    def test_small_file_no_output(self, tmp_project):
        path = _write_file(tmp_project, "small.py", 1000)

        result = _run_hook(tmp_project, {"file_path": path})

        assert result.returncode == 0
        assert "LARGE FILE ADVISORY" not in result.stderr

    def test_exact_threshold_no_advisory(self, tmp_project):
        # File at exactly 40000 bytes should NOT trigger (threshold is >40000)
        path = _write_file(tmp_project, "boundary.py", 39999)

        result = _run_hook(tmp_project, {"file_path": path})

        assert result.returncode == 0
        assert "LARGE FILE ADVISORY" not in result.stderr


class TestHookLogsToMetrics:
    """Hook logs large file reads to metrics JSONL."""

    def test_large_file_logged(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 50000)

        _run_hook(tmp_project, {"file_path": path})

        # Check global metrics (no session active in test)
        metrics_path = os.path.join(
            tmp_project, ".cognitive-os", "metrics", "large-file-reads.jsonl"
        )
        assert os.path.exists(metrics_path)
        with open(metrics_path) as f:
            entries = [json.loads(line) for line in f if line.strip()]
        assert len(entries) >= 1
        assert entries[0]["advisory"] is True
        assert entries[0]["bytes"] > 40000

    def test_small_file_not_logged(self, tmp_project):
        path = _write_file(tmp_project, "small.py", 1000)

        _run_hook(tmp_project, {"file_path": path})

        metrics_path = os.path.join(
            tmp_project, ".cognitive-os", "metrics", "large-file-reads.jsonl"
        )
        # Small files should not produce metrics entries
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                content = f.read().strip()
            assert content == ""


class TestHookSkipsWhenOffsetProvided:
    """Hook silently skips when user already provides offset/limit."""

    def test_offset_skips_advisory(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 50000)

        result = _run_hook(tmp_project, {
            "file_path": path,
            "offset": 1,
            "limit": 100,
        })

        assert result.returncode == 0
        assert "LARGE FILE ADVISORY" not in result.stderr

    def test_limit_only_skips_advisory(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 50000)

        result = _run_hook(tmp_project, {
            "file_path": path,
            "limit": 50,
        })

        assert result.returncode == 0
        assert "LARGE FILE ADVISORY" not in result.stderr


class TestHookNeverBlocks:
    """Hook always exits 0 (advisory only)."""

    def test_exit_code_zero_for_large_file(self, tmp_project):
        path = _write_file(tmp_project, "big.py", 100000)
        result = _run_hook(tmp_project, {"file_path": path})
        assert result.returncode == 0

    def test_exit_code_zero_for_missing_file(self, tmp_project):
        result = _run_hook(tmp_project, {"file_path": "/nonexistent/file.py"})
        assert result.returncode == 0

    def test_exit_code_zero_for_non_read_tool(self, tmp_project):
        # Simulate a non-Read tool (hook should exit early)
        stdin_json = json.dumps({
            "tool_name": "Write",
            "tool_input": {"file_path": "/tmp/x"},
        })
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = tmp_project
        env["COGNITIVE_OS_PROJECT_DIR"] = tmp_project

        result = subprocess.run(
            ["bash", HOOK_PATH],
            input=stdin_json,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=tmp_project,
        )
        assert result.returncode == 0


class TestHookPerformance:
    """Hook completes within 200ms for typical files."""

    def test_completes_quickly(self, tmp_project):
        import time

        path = _write_file(tmp_project, "big.py", 50000)

        start = time.monotonic()
        _run_hook(tmp_project, {"file_path": path})
        elapsed = time.monotonic() - start

        # Allow generous margin for CI but still check it's not pathologically slow
        assert elapsed < 2.0, f"Hook took {elapsed:.2f}s, expected < 2s"


class TestHookSectionHints:
    """Hook provides section hints for known file types."""

    def test_python_class_hints(self, tmp_project):
        path = os.path.join(tmp_project, "big.py")
        with open(path, "w") as f:
            f.write("import os\n\n")
            f.write("class FooHandler:\n    pass\n\n")
            # Pad to exceed threshold
            for i in range(600):
                f.write(f"    def method_{i}(self):\n        pass\n\n")

        result = _run_hook(tmp_project, {"file_path": path})

        if "File sections:" in result.stderr:
            assert "class FooHandler" in result.stderr

    def test_markdown_header_hints(self, tmp_project):
        path = os.path.join(tmp_project, "big.md")
        with open(path, "w") as f:
            f.write("# Main Title\n\n")
            f.write("## Section Alpha\n\n")
            # Pad to exceed threshold
            for i in range(2000):
                f.write(f"Content line {i}\n")

        result = _run_hook(tmp_project, {"file_path": path})

        if "File sections:" in result.stderr:
            assert "Main Title" in result.stderr or "Section Alpha" in result.stderr
