"""ADR-256 Phase 5 observable primitive self-use contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from lib.trace_joiner import build_run_trace

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_trace_joiner_answers_itinerary_and_intervention_questions(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "codebase-itinerary.jsonl").write_text(
        '{"timestamp":"2026-05-09T00:00:00Z","session_id":"s1","tool_use_id":"t1","tool":"Read","target_ref":{"kind":"path-hash","hash_sha256_12":"aaa"}}\n',
        encoding="utf-8",
    )
    (metrics / "primitive-interventions.jsonl").write_text(
        '{"schema_version":"primitive-intervention.v1","timestamp":"2026-05-09T00:00:01Z","session_id":"s1","tool_use_id":"t2","primitive_id":"destructive-git-blocker","primitive_family":"hook","action_kind":"block","reason_code":"destructive_git_op"}\n',
        encoding="utf-8",
    )

    payload = build_run_trace(tmp_path, session_id="s1")

    assert payload["streams"] == {"codebase-itinerary": 1, "primitive-interventions": 1}
    summary = payload["observable_self_use"]
    assert summary["schema_version"] == "observable-primitive-self-use.v1"
    assert summary["has_observable_self_use"] is True
    assert summary["has_codebase_itinerary"] is True
    assert summary["has_runtime_intervention"] is True
    assert summary["inspected_tools"] == {"Read": 1}
    assert summary["interventions_by_primitive"] == {"destructive-git-blocker": 1}
    assert summary["interventions_by_action"] == {"block": 1}
    assert summary["correlated_tool_use_ids"] == ["t2"]


def test_cos_observe_primitives_cli_reports_summary_without_writing(tmp_path: Path) -> None:
    metrics = tmp_path / ".cognitive-os" / "metrics"
    metrics.mkdir(parents=True)
    (metrics / "primitive-interventions.jsonl").write_text(
        '{"schema_version":"primitive-intervention.v1","timestamp":"2026-05-09T00:00:01Z","session_id":"s2","tool_use_id":"t9","primitive_id":"large-file-advisor","primitive_family":"hook","action_kind":"advise","reason_code":"large_file_read"}\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / "cos-observe-primitives"), "--project-dir", str(tmp_path), "--session-id", "s2", "--no-write", "--json"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    report = json.loads(result.stdout)
    assert report["schema_version"] == "cos-observe-primitives.v1"
    assert report["observable_self_use"]["primitive_intervention_events"] == 1
    assert not (tmp_path / ".cognitive-os" / "reports" / "run-trace-latest.json").exists()
