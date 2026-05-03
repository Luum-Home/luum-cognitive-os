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
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps(_settings(["hooks/session-init.sh"])), encoding="utf-8")
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
    assert report["active_session_start_hook_count"] == 1
    assert report["projection_source"] == "generated_profile"
    assert report["active_projection_matches_profile"] is True
    assert report["hooks"][0]["p50_ms"] == 20


def test_core_budget_distinguishes_generated_core_from_active_maintainer_settings(tmp_path: Path) -> None:
    _manifest(tmp_path)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps(_settings(["hooks/session-init.sh", "hooks/validation-lock-cleanup.sh"])),
        encoding="utf-8",
    )
    (tmp_path / ".cognitive-os" / "metrics").mkdir(parents=True)

    with patch.object(budget, "generated_settings", return_value=_settings(["hooks/session-init.sh"])):
        report = budget.build_report("core", tmp_path)

    assert report["status"] == "pass"
    assert report["projection_source"] == "generated_profile"
    assert report["session_start_hook_count"] == 1
    assert report["active_session_start_hook_count"] == 2
    assert report["active_projection_matches_profile"] is False
