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


def _fixture_source(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    _write(root / "manifests" / "primitive-lifecycle.yaml", yaml.safe_dump({"primitives": []}))
    _write(root / "manifests" / "primitive-contracts.yaml", "schema_version: primitive-contracts.v1\ncontracts: []\n")
    _write(root / "manifests" / "harness-projection.yaml", "schema_version: harness-projection.v1\nharnesses: []\n")
    return root


def test_consumer_alias_is_positional_and_deterministic() -> None:
    assert [smoke.consumer_alias(i) for i in (0, 1, 25, 26, 27)] == [
        "consumidor-a",
        "consumidor-b",
        "consumidor-z",
        "consumidor-aa",
        "consumidor-ab",
    ]


def test_written_reports_carry_aliases_never_the_registered_name(tmp_path: Path, monkeypatch, capsys) -> None:
    real_names = ["Zeta Private Wallet", "Alpha Client Store"]
    root = _fixture_source(tmp_path)
    installations = []
    for name in real_names:
        consumer = tmp_path / name.lower().replace(" ", "-")
        consumer.mkdir()
        installations.append({"source": str(root.resolve()), "path": str(consumer), "project_name": name, "version": "1"})
    registry = tmp_path / "installations.json"
    registry.write_text(json.dumps({"installations": installations}), encoding="utf-8")
    out_json = tmp_path / "out" / "latest.json"
    out_md = tmp_path / "out" / "latest.md"
    out_json.parent.mkdir()
    monkeypatch.setattr(smoke, "DEFAULT_JSON", out_json)
    monkeypatch.setattr(smoke, "DEFAULT_MD", out_md)

    smoke.main(["--project-dir", str(root), "--registry", str(registry), "--limit", "5", "--write-report"])
    first = out_json.read_text(encoding="utf-8"), out_md.read_text(encoding="utf-8")
    written = "\n".join(first).lower()

    for name in real_names:
        assert name.lower() not in written
        assert name.lower().replace(" ", "-") not in written
    # Registry order, not alphabetical order of the names.
    rows = json.loads(first[0])["consumer_rows"]
    assert sorted(row["consumer_id"] for row in rows) == ["consumidor-a", "consumidor-b"]
    assert "`consumidor-a`" in first[1]

    capsys.readouterr()
    smoke.main(["--project-dir", str(root), "--registry", str(registry), "--limit", "5", "--write-report", "--reveal-names"])
    revealed = capsys.readouterr().out
    assert "consumidor-a\tZeta Private Wallet" in revealed
    assert "consumidor-b\tAlpha Client Store" in revealed
    # The flag reveals on stdout only: the tracked artifacts stay aliased.
    again = "\n".join((out_json.read_text(encoding="utf-8"), out_md.read_text(encoding="utf-8"))).lower()
    for name in real_names:
        assert name.lower() not in again
