from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from lib.publication_safety import (
    CONFIG_SCHEMA_VERSION,
    SCHEMA_VERSION,
    PublicationSafetyConfigError,
    build_receipt,
    load_config,
    parse_commands,
)


def write_gate(path: Path, body: str) -> Path:
    path.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


def write_config(root: Path, commands: list[dict], *, enabled: bool = True) -> Path:
    path = root / "publication-safety.json"
    path.write_text(
        json.dumps({"schema_version": CONFIG_SCHEMA_VERSION, "enabled": enabled, "commands": commands}, indent=2),
        encoding="utf-8",
    )
    return path


@pytest.mark.unit
def test_passing_required_gates_emit_public_release_ready_receipt(tmp_path: Path) -> None:
    write_gate(tmp_path / "pass_gate.py", "import json; print(json.dumps({'schema': 'consumer.gate.v0', 'status': 'pass'}))\n")
    config = write_config(tmp_path, [{"id": "pre_publication", "command": [str(tmp_path / "pass_gate.py")]}])

    receipt = build_receipt(tmp_path, config)

    assert receipt["schema_version"] == SCHEMA_VERSION
    assert receipt["status"] == "pass"
    assert receipt["claim"]["public_release_ready"] is True
    assert receipt["steps"][0]["payload_schema"] == "consumer.gate.v0"
    assert receipt["steps"][0]["argv"] == [str(tmp_path / "pass_gate.py")]
    assert "stdout_path" not in receipt["steps"][0]


@pytest.mark.unit
def test_required_nonzero_gate_fails_receipt_without_leaking_stdout(tmp_path: Path) -> None:
    write_gate(
        tmp_path / "fail_gate.py",
        "import sys; print('SECRET_SENTINEL_STDOUT'); print('SECRET_SENTINEL_STDERR', file=sys.stderr); sys.exit(7)\n",
    )
    config = write_config(tmp_path, [{"id": "raw_secret_scan", "command": [str(tmp_path / "fail_gate.py")], "required": True}])

    receipt = build_receipt(tmp_path, config)
    encoded = json.dumps(receipt)

    assert receipt["status"] == "fail"
    assert receipt["summary"]["required_failed"] == ["raw_secret_scan"]
    assert receipt["steps"][0]["exit_code"] == 7
    assert receipt["steps"][0]["reason_code"] == "exit_code"
    assert "SECRET_SENTINEL" not in encoded
    assert receipt["steps"][0]["stdout_bytes"] > 0
    assert receipt["steps"][0]["stderr_bytes"] > 0


@pytest.mark.unit
def test_optional_failing_gate_warns_not_fails(tmp_path: Path) -> None:
    write_gate(tmp_path / "optional.py", "import sys; sys.exit(1)\n")
    config = write_config(tmp_path, [{"id": "optional_arena", "command": [str(tmp_path / "optional.py")], "required": False}])

    receipt = build_receipt(tmp_path, config)

    assert receipt["status"] == "warn"
    assert receipt["summary"]["warnings"] == ["optional_arena"]
    assert receipt["summary"]["required_failed"] == []
    assert receipt["claim"]["public_release_ready"] is False


@pytest.mark.unit
def test_json_payload_fail_status_fails_even_with_zero_exit(tmp_path: Path) -> None:
    write_gate(tmp_path / "payload_fail.py", "import json; print(json.dumps({'status': 'fail'}))\n")
    config = write_config(tmp_path, [{"id": "public_readiness", "command": [str(tmp_path / "payload_fail.py")]}])

    receipt = build_receipt(tmp_path, config)

    assert receipt["status"] == "fail"
    assert receipt["steps"][0]["payload_status"] == "fail"
    assert receipt["steps"][0]["reason_code"] == "payload_status"


@pytest.mark.unit
def test_progress_output_with_final_json_is_parsed(tmp_path: Path) -> None:
    write_gate(tmp_path / "progress.py", "import json; print('## step'); print(json.dumps({'schema_version': 'x/v0', 'status': 'pass'}))\n")
    config = write_config(tmp_path, [{"id": "aggregate", "command": [str(tmp_path / "progress.py")]}])

    receipt = build_receipt(tmp_path, config)

    assert receipt["status"] == "pass"
    assert receipt["steps"][0]["payload_schema"] == "x/v0"


@pytest.mark.unit
def test_disabled_config_yields_skipped_receipt(tmp_path: Path) -> None:
    config = write_config(tmp_path, [], enabled=False)

    receipt = build_receipt(tmp_path, config)

    assert receipt["status"] == "skipped"
    assert receipt["enabled"] is False
    assert receipt["steps"] == []


@pytest.mark.unit
def test_parse_commands_rejects_duplicate_ids(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, [{"id": "x", "run": "echo ok"}, {"id": "x", "run": "echo ok"}]))

    with pytest.raises(PublicationSafetyConfigError, match="duplicate"):
        parse_commands(config)


@pytest.mark.unit
def test_run_string_is_split_without_shell(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, [{"id": "echo", "run": "python3 -c 'print(123)'"}]))

    command = parse_commands(config)[0]

    assert command.argv == ("python3", "-c", "print(123)")
