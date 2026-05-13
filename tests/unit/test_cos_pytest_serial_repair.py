from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts" / "cos-pytest-serial-repair"


def _load_runner():
    loader = importlib.machinery.SourceFileLoader("cos_pytest_serial_repair", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


def test_auto_mode_uses_files_for_directories():
    runner = _load_runner()
    assert runner.should_use_file_mode("auto", ["tests/"]) is True
    assert runner.should_use_file_mode("auto", ["tests/unit/test_rate_limiter.py::test_x"]) is False
    assert runner.should_use_file_mode("suite", ["tests/"]) is False


def test_file_mode_records_completed_chunks_before_failure(tmp_path: Path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    (tests_dir / "test_b.py").write_text("def test_b():\n    assert False\n", encoding="utf-8")
    state_file = tmp_path / ".state.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "tests/",
            "--mode",
            "files",
            "--timeout-seconds",
            "30",
            "--chunk-timeout-seconds",
            "10",
            "--state-file",
            str(state_file),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "PYTEST_CHUNK_RC 1 tests/test_b.py" in result.stdout
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["completed"] == ["tests/test_a.py"]
