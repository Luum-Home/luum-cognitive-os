from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import yaml

import scripts.session_start_budget as budget


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifests" / "primitive-lifecycle.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "primitives": [
                    {"id": "hooks/session-init.sh", "distribution": "core", "maturity": "advisory", "lifecycle_state": "advisory"},
                    {"id": "hooks/lab.sh", "distribution": "lab", "maturity": "observe", "lifecycle_state": "sandbox"},
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _settings(paths: list[str]) -> dict:
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "",
                    "hooks": [
                        {"type": "command", "command": f'bash "$CLAUDE_PROJECT_DIR/scripts/hook-timing-wrapper.sh" SessionStart "$CLAUDE_PROJECT_DIR/{path}"'}
                        for path in paths
                    ],
                }
            ]
        }
    }


def test_core_budget_fails_lab_session_start(tmp_path: Path) -> None:
    _manifest(tmp_path)
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)
    with patch.object(budget, "generated_settings", return_value=_settings(["hooks/session-init.sh", "hooks/lab.sh"])):
        report = budget.build_report("core", tmp_path)

    assert report["status"] == "fail"
    assert report["counts_by_tier"]["lab"] == 1
    assert any(item["id"] == "core-session-start-lab-hooks" for item in report["findings"])


def test_core_budget_passes_small_core_projection(tmp_path: Path) -> None:
    _manifest(tmp_path)
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "hook-timing.jsonl").write_text(
        json.dumps({"event": "SessionStart", "hook": "hooks/session-init.sh", "duration_ms": 10}) + "\n"
        + json.dumps({"event": "SessionStart", "hook": "hooks/session-init.sh", "duration_ms": 30}) + "\n",
        encoding="utf-8",
    )
    with patch.object(budget, "generated_settings", return_value=_settings(["hooks/session-init.sh"])):
        report = budget.build_report("core", tmp_path)

    assert report["status"] == "pass"
    assert report["session_start_hook_count"] == 1
    assert report["hooks"][0]["p50_ms"] == 20
