from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-test-repair-loop"


def _load_runner():
    loader = importlib.machinery.SourceFileLoader("cos_test_repair_loop", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


@pytest.mark.unit
def test_repair_loop_extracts_failed_nodeids_and_reruns_individual(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_fail.py").write_text("def test_fail():\n    assert False\n", encoding="utf-8")
    report = tmp_path / "report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--full-command",
            f"{sys.executable} -m pytest tests -q --tb=short",
            "--timeout-seconds",
            "30",
            "--individual-timeout-seconds",
            "10",
            "--report",
            str(report),
            "--allow-dirty-after",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=40,
    )

    assert result.returncode == 1
    assert "TEST_REPAIR_LOOP_FAILED_NODEIDS" in result.stdout
    assert "tests/test_fail.py::test_fail" in result.stdout
    assert "TEST_REPAIR_LOOP_INDIVIDUAL_RERUN tests/test_fail.py::test_fail 1" in result.stdout
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["failed_nodeids"] == ["tests/test_fail.py::test_fail"]


@pytest.mark.unit
def test_repair_loop_timeout_is_bounded(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--full-command",
            f"{sys.executable} -c 'import time; time.sleep(5)'",
            "--timeout-seconds",
            "1",
            "--serial-timeout-seconds",
            "1",
            "--report",
            str(tmp_path / "report.json"),
            "--allow-dirty-after",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 124
    assert "TEST_REPAIR_LOOP_TIMEOUT" in result.stdout


@pytest.mark.unit
def test_repair_loop_detects_dirty_start(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)
    tracked.write_text("two\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--full-command", "true", "--require-clean-start"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=10,
    )

    assert result.returncode == 3
    assert "TEST_REPAIR_LOOP_DIRTY_START" in result.stdout


@pytest.mark.unit
def test_repair_loop_detects_dirty_after_success(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=tmp_path, check=True, capture_output=True)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--full-command",
            f"{sys.executable} -c 'from pathlib import Path; Path(\"tracked.txt\").write_text(\"two\\n\")'",
            "--timeout-seconds",
            "10",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 3
    assert "TEST_REPAIR_LOOP_DIRTY_AFTER_RUN" in result.stdout


@pytest.mark.unit
def test_git_status_helper_ignores_untracked_files(tmp_path: Path) -> None:
    runner = _load_runner()
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")
    assert runner.git_tracked_status(tmp_path) == []


@pytest.mark.unit
def test_repair_loop_prefers_repo_venv_python(tmp_path: Path) -> None:
    runner = _load_runner()
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.write_text("#!/bin/sh\n", encoding="utf-8")
    assert runner.preferred_python(tmp_path) == str(python_path)
