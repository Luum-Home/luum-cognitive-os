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
    (root / "manifests").mkdir(parents=True)
    (root / "cognitive-os.yaml").write_text(yaml.safe_dump({"project": {"phase": "reconstruction"}}))
    (root / "manifests" / "harness-projection.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "harness-projection.v1",
                "harnesses": [
                    {"id": "claude", "display_name": "Claude Code", "status": "implemented", "projection_mode": "native-settings"},
                    {"id": "cursor", "display_name": "Cursor", "status": "planned", "projection_mode": "ide-rules-or-wrapper"},
                ],
            }
        )
    )
    (root / "manifests" / "primitive-projection-profiles.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": "primitive-projection-profiles.v1",
                "profiles": {
                    "default": {"description": "default profile"},
                    "full": {"description": "full profile"},
                },
                "projection_classes": {
                    "shared": {},
                    "default": {},
                    "full": {},
                    "profile-driver": {},
                    "maintainer-only": {},
                },
                "profile_driver_scripts": [
                    {"path": "scripts/projected.sh", "class": "profile-driver", "source_manifest": "test"},
                ],
            }
        )
    )
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
    assert payload["harness_projection"]["claude"]["status"] == "implemented"
    assert payload["harness_projection"]["cursor"]["status"] == "planned"
    assert payload["adapters"]["projection_profiles"]["status"] == "ok"
    compact = acc_pipeline.compact_summary(payload)
    assert compact["schema_version"] == "acc.compact.v1"
    assert compact["context_diet"]["read_this_first"] == "docs/acc/latest-compact.md"


def test_projected_readiness_row_becomes_aligned(tmp_path: Path) -> None:
    row = {
        "path": "skills/cos-status/SKILL.md",
        "role": "compatibility-wrapper",
        "role_source": "test",
        "consumer_accessibility": "repo-skill-not-projectable",
        "evidence": [],
    }

    cap = acc_pipeline.capability_from_readiness(
        row,
        "skills",
        {"skills/cos-status/SKILL.md": {"harnesses": ["claude", "codex"], "paths": [".cognitive-os/skills/cos/cos-status/SKILL.md"]}},
    )

    assert cap.mapping_status == "aligned"
    assert cap.consumer_accessibility == "projected-consumer-surface"
    assert "projected_harnesses:claude,codex" in cap.evidence


def test_harness_registry_reports_planned_harnesses(tmp_path: Path) -> None:
    root = make_repo(tmp_path)

    status, manifest = acc_pipeline.load_harness_projection(root)
    summary = acc_pipeline.harness_projection_summary(manifest, status)

    assert status.status == "ok"
    assert summary["claude"]["status"] == "implemented"
    assert summary["cursor"]["status"] == "planned"
    assert "cursor" not in acc_pipeline.implemented_harness_ids(manifest)


def test_refresh_adapters_includes_primitive_duplication(monkeypatch, tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    seen: list[str] = []

    def fake_run_json_command(root_path, name, command, timeout=120):
        seen.append(name)
        return acc_pipeline.AdapterStatus("ok", name, " ".join(command), summary={}), {}

    monkeypatch.setattr(acc_pipeline, "run_json_command", fake_run_json_command)

    adapters = acc_pipeline.refresh_adapters(root, include_slow=False)

    assert "primitive_duplication" in adapters
    assert "primitive_duplication" in seen


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
