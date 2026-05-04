from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "acc_pipeline.py"
spec = importlib.util.spec_from_file_location("acc_pipeline", MODULE_PATH)
assert spec and spec.loader
acc_pipeline = importlib.util.module_from_spec(spec)
sys.modules["acc_pipeline"] = acc_pipeline
spec.loader.exec_module(acc_pipeline)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "reports").mkdir(parents=True)
    (root / "cognitive-os.yaml").write_text(yaml.safe_dump({"project": {"phase": "reconstruction"}}))
    script_payload = {
        "summary": {},
        "scripts": [
            {
                "path": "scripts/projected.sh",
                "role": "agentic-primitive",
                "role_source": "lifecycle",
                "lifecycle_id": "scripts/projected.sh",
                "lifecycle_state": "candidate",
                "consumer_accessibility": "install-profile-managed",
                "supported_harnesses": ["shell"],
                "distribution": "core",
                "evidence": ["test"],
            },
            {
                "path": "scripts/local.py",
                "role": "maintainer-tool",
                "role_source": "default",
                "consumer_accessibility": "so-local-only",
                "supported_harnesses": [],
                "evidence": [],
            },
        ],
    }
    write_json(root / "docs" / "reports" / "primitive-readiness-ledger-scripts-latest.json", script_payload)
    for family in ("hooks", "skills", "rules"):
        write_json(
            root / "docs" / "reports" / f"primitive-readiness-ledger-{family}-latest.json",
            {
                "summary": {},
                "items": [
                    {
                        "path": f"{family}/x",
                        "family": family,
                        "role": "runtime-safety" if family == "hooks" else "context-only",
                        "role_source": "test",
                        "lifecycle_id": f"{family}/x" if family == "hooks" else None,
                        "lifecycle_state": "advisory" if family == "hooks" else None,
                        "consumer_accessibility": "projected-consumer-surface" if family == "hooks" else "so-local-only",
                        "supported_harnesses": ["claude"] if family == "hooks" else [],
                        "evidence": ["test"],
                    }
                ],
            },
        )
    write_json(
        root / "docs" / "reports" / "docs-execution-latest.json",
        {
            "summary": {"items": 1},
            "rows": [
                {
                    "path": "docs/x.md",
                    "line": 3,
                    "inferred_status": "stale",
                    "item": "done claim references missing proof",
                    "evidence": ["missing_path:x"],
                    "next_action": "update docs",
                }
            ],
        },
    )
    return root


def test_build_report_maps_readiness_rows_to_acc_statuses(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    payload = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)

    statuses = {cap["id"]: cap["mapping_status"] for cap in payload["capabilities"]}

    assert statuses["script:scripts/projected.sh"] == "partial"
    assert statuses["script:scripts/local.py"] == "unverified"
    assert statuses["hook:hooks/x"] == "aligned"
    assert payload["summary"]["stale_weight"] >= 2
    assert payload["gate"]["phase"] == "reconstruction"
    assert payload["persistence"]["engram"]["status"] == "unavailable"
    compact = acc_pipeline.compact_summary(payload)
    assert compact["schema_version"] == "acc.compact.v1"
    assert compact["context_diet"]["read_this_first"] == "docs/acc/latest-compact.md"


def test_write_report_outputs_json_markdown_and_history(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    payload = acc_pipeline.build_report(root, refresh=False, include_slow=False, fail_on_warn=False)

    acc_pipeline.write_json(root / "docs" / "acc" / "latest.json", payload)
    (root / "docs" / "acc").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "acc" / "latest.md").write_text(acc_pipeline.render_markdown(payload))
    (root / "docs" / "acc" / "latest-compact.md").write_text(acc_pipeline.render_compact_markdown(payload))
    acc_pipeline.append_history(root, payload)

    assert json.loads((root / "docs" / "acc" / "latest.json").read_text())["schema_version"] == "acc.report.v1"
    assert "Agent Capability Coverage" in (root / "docs" / "acc" / "latest.md").read_text()
    assert "Context Diet Rule" in (root / "docs" / "acc" / "latest-compact.md").read_text()
    assert (root / ".cognitive-os" / "metrics" / "acc-pipeline-history.jsonl").exists()
