"""ADR-256 Phase 3 codebase itinerary contracts."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOOK = PROJECT_ROOT / "hooks" / "codebase-itinerary-capture.sh"
CONFIG = PROJECT_ROOT / "cognitive-os.yaml"


def _run_hook(project_dir: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COGNITIVE_OS_PROJECT_DIR": str(project_dir),
            "COGNITIVE_OS_SESSION_ID": "itinerary-session",
            "COS_TASK_ID": "itinerary-task",
            "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
        }
    )
    return subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        cwd=PROJECT_ROOT,
        check=False,
    )


def _rows(project_dir: Path) -> list[dict]:
    target = project_dir / ".cognitive-os" / "metrics" / "codebase-itinerary.jsonl"
    assert target.exists(), "codebase itinerary metric was not written"
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_hook_is_registered_for_post_tool_read_grep_glob_ls():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    hook = config["harness"]["hooks"].get("codebase-itinerary-capture")

    assert hook == {
        "script": "hooks/codebase-itinerary-capture.sh",
        "event": "PostToolUse",
        "matcher": "Read|Grep|Glob|LS",
        "scope": "os-only",
    }


def test_read_capture_records_only_content_free_path_metadata(tmp_path):
    secret_path = tmp_path / "secrets" / "prod-token.env"
    payload = {
        "tool_name": "Read",
        "tool_input": {"file_path": str(secret_path)},
        "tool_response": {"content": "sk-live-raw-secret-value"},
    }

    result = _run_hook(tmp_path, payload)

    assert result.returncode == 0
    row = _rows(tmp_path)[0]
    serialized = json.dumps(row, sort_keys=True)
    assert row["schema_version"] == "codebase-itinerary.v1"
    assert row["tool"] == "Read"
    assert row["action_kind"] == "read"
    assert row["target_kind"] == "file"
    assert row["session_id"] == "itinerary-session"
    assert row["privacy"] == {
        "content_free": True,
        "raw_paths": False,
        "raw_patterns": False,
        "raw_tool_output": False,
    }
    assert row["target_ref"]["hash_sha256_12"]
    assert row["target_ref"]["path_ext"] == "env"
    assert "prod-token" not in serialized
    assert str(secret_path) not in serialized
    assert "sk-live-raw-secret-value" not in serialized


def test_grep_and_glob_do_not_store_raw_patterns(tmp_path):
    grep_payload = {
        "tool_name": "Grep",
        "tool_input": {
            "pattern": "AKIA[0-9A-Z]{16}|password=super-secret",
            "path": str(tmp_path / "src"),
            "include": "*.py",
        },
        "tool_response": {"content": "password=super-secret"},
    }
    glob_payload = {
        "tool_name": "Glob",
        "tool_input": {
            "pattern": "**/*secret*.pem",
            "path": str(tmp_path),
        },
        "tool_response": {"content": "secrets/prod.pem"},
    }

    assert _run_hook(tmp_path, grep_payload).returncode == 0
    assert _run_hook(tmp_path, glob_payload).returncode == 0

    rows = _rows(tmp_path)
    assert [row["tool"] for row in rows] == ["Grep", "Glob"]
    assert rows[0]["selector_ref"]["kind"] == "grep-pattern"
    assert rows[1]["selector_ref"]["kind"] == "glob-pattern"
    serialized = json.dumps(rows, sort_keys=True)
    for forbidden in (
        "AKIA",
        "password=super-secret",
        "**/*secret*.pem",
        "*.py",
        "secrets/prod.pem",
    ):
        assert forbidden not in serialized


def test_non_itinerary_tools_are_ignored(tmp_path):
    result = _run_hook(tmp_path, {"tool_name": "Bash", "tool_input": {"command": "pwd"}})

    assert result.returncode == 0
    assert not (tmp_path / ".cognitive-os" / "metrics" / "codebase-itinerary.jsonl").exists()
