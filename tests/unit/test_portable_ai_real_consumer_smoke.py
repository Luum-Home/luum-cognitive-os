from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import portable_ai_real_consumer_smoke as smoke


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_real_consumer_smoke_projects_overlay_into_shadows_without_mutating_consumers(tmp_path: Path) -> None:
    root = tmp_path / "source"
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _write(consumer / ".ai" / "existing.txt", "unchanged\n")
    _write(
        root / "manifests" / "primitive-lifecycle.yaml",
        yaml.safe_dump(
            {
                "primitives": [
                    {
                        "id": "hooks/example.sh",
                        "kind": "hook",
                        "supported_harnesses": ["codex"],
                        "runtime_projection": True,
                        "projection_targets": ["hooks/example.sh"],
                        "behavior_evidence": "unit fixture",
                    }
                ]
            }
        ),
    )
    _write(root / "manifests" / "primitive-contracts.yaml", "schema_version: primitive-contracts.v1\ncontracts: []\n")
    _write(root / "manifests" / "harness-projection.yaml", "schema_version: harness-projection.v1\nharnesses: []\n")
    registry = tmp_path / "installations.json"
    registry.write_text(
        json.dumps({"installations": [{"source": str(root.resolve()), "path": str(consumer), "project_name": "Consumer A", "version": "1"}]}),
        encoding="utf-8",
    )

    report = smoke.build_report(root, registry, limit=1)

    assert report["schema_version"] == "portable-ai-real-consumer-smoke.v1"
    assert report["status"] == "pass"
    assert report["tested_consumer_count"] == 1
    assert report["consumer_rows"][0]["actual_consumer_unchanged"] is True
    assert (consumer / ".ai" / "existing.txt").read_text(encoding="utf-8") == "unchanged\n"
