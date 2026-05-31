from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest


def write_gate(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)


def write_config(root: Path, commands: list[dict], *, enabled: bool = True) -> Path:
    path = root / "publication-safety.json"
    path.write_text(json.dumps({"schema_version": "publication-safety-config/v0", "enabled": enabled, "commands": commands}), encoding="utf-8")
    return path


@pytest.mark.behavior
def test_publication_safety_cli_writes_receipt_and_exits_zero_on_pass(project_root: Path, tmp_path: Path) -> None:
    write_gate(tmp_path / "pass.py", "import json; print(json.dumps({'status': 'pass'}))\n")
    config = write_config(tmp_path, [{"id": "pre_publication_gate", "command": [str(tmp_path / "pass.py")]}])
    output = tmp_path / ".cognitive-os/receipts/publication-safety/summary.json"

    result = subprocess.run(
        [str(project_root / "scripts/cos-publication-safety"), "--project-dir", str(tmp_path), "--config", str(config), "--output", str(output), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "pass"
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "publication-safety-receipt/v0"


@pytest.mark.behavior
def test_publication_safety_cli_exit_2_on_required_failure(project_root: Path, tmp_path: Path) -> None:
    write_gate(tmp_path / "fail.py", "import sys; sys.exit(3)\n")
    config = write_config(tmp_path, [{"id": "history_publication", "command": [str(tmp_path / "fail.py")]}])

    result = subprocess.run(
        [str(project_root / "scripts/cos-publication-safety"), "--project-dir", str(tmp_path), "--config", str(config), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "fail"


@pytest.mark.behavior
def test_publication_safety_cli_strict_exit_2_on_optional_warning(project_root: Path, tmp_path: Path) -> None:
    write_gate(tmp_path / "warn.py", "import sys; sys.exit(1)\n")
    config = write_config(tmp_path, [{"id": "optional_arena", "command": [str(tmp_path / "warn.py")], "required": False}])

    result = subprocess.run(
        [str(project_root / "scripts/cos-publication-safety"), "--project-dir", str(tmp_path), "--config", str(config), "--json", "--strict"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "warn"


@pytest.mark.behavior
def test_publication_safety_cli_write_step_logs_is_explicit(project_root: Path, tmp_path: Path) -> None:
    write_gate(tmp_path / "log.py", "print('LOCAL_DIAGNOSTIC')\n")
    config = write_config(tmp_path, [{"id": "docs_link_check", "command": [str(tmp_path / "log.py")]}])
    output = tmp_path / "receipt.json"

    result = subprocess.run(
        [str(project_root / "scripts/cos-publication-safety"), "--project-dir", str(tmp_path), "--config", str(config), "--output", str(output), "--write-step-logs", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    stdout_path = Path(payload["steps"][0]["stdout_path"])
    assert stdout_path.exists()
    assert stdout_path.read_text(encoding="utf-8").strip() == "LOCAL_DIAGNOSTIC"


@pytest.mark.behavior
def test_cos_dispatcher_routes_publication_safety(project_root: Path) -> None:
    result = subprocess.run(
        [str(project_root / "scripts/cos"), "publication", "safety", "--allow-missing-config", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode in {0, 2}
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "publication-safety-receipt/v0"


@pytest.mark.behavior
def test_publication_safety_hook_noops_without_config(project_root: Path, tmp_path: Path) -> None:
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["COS_PUBLICATION_SAFETY_CLI"] = str(project_root / "scripts/cos-publication-safety")
    result = subprocess.run(
        ["bash", str(project_root / "hooks/publication-safety.sh")],
        input=json.dumps({"tool_input": {"command": "git push origin main"}}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0


@pytest.mark.behavior
def test_publication_safety_hook_blocks_required_failure(project_root: Path, tmp_path: Path) -> None:
    write_gate(tmp_path / "fail.py", "import sys; sys.exit(9)\n")
    config = write_config(tmp_path, [{"id": "pre_publication_gate", "command": [str(tmp_path / "fail.py")]}])
    env = os.environ.copy()
    env["COGNITIVE_OS_PROJECT_DIR"] = str(tmp_path)
    env["COS_PUBLICATION_SAFETY_CONFIG"] = str(config)
    env["COS_PUBLICATION_SAFETY_CLI"] = str(project_root / "scripts/cos-publication-safety")
    env["COS_PUBLICATION_SAFETY_REQUIRED"] = "1"

    result = subprocess.run(
        ["bash", str(project_root / "hooks/publication-safety.sh")],
        input=json.dumps({"tool_input": {"command": "git push origin main"}}),
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 2
    assert "publication-safety gates did not pass" in result.stderr
