from __future__ import annotations

import json
from pathlib import Path

from lib.script_exposure_audit import build_audit, classify_script, render_markdown


def _row(path: str, role: str, *, skill: int = 0, total: int = 0, families: dict[str, int] | None = None) -> dict:
    consumers = []
    for family, count in (families or {}).items():
        for idx in range(count):
            consumers.append({"family": family, "path": f"{family}/consumer-{idx}"})
    return {
        "path": path,
        "role": role,
        "skill_consumers": skill,
        "total_consumers": total,
        "consumer_families": families or {},
        "consumers": consumers,
    }


def test_classify_script_priorities() -> None:
    assert classify_script(_row("scripts/agentic", "agentic-primitive"))["priority"] == "P0"
    assert classify_script(_row("scripts/maint", "maintainer-tool"))["priority"] == "P1"
    assert classify_script(_row("scripts/maint-doc", "maintainer-tool", total=2, families={"doc": 1, "test": 1}))["priority"] == "P2"
    assert classify_script(_row("scripts/lab", "lab"))["priority"] == "P3"
    assert classify_script(_row("scripts/skilled", "agentic-primitive", skill=1, total=1, families={"skill": 1}))["priority"] == "OK"


def test_build_audit_summary_and_markdown(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "schema_version": "primitive-readiness-ledger/v1",
                "scripts": [
                    _row("scripts/agentic", "agentic-primitive"),
                    _row("scripts/maint", "maintainer-tool"),
                    _row("scripts/maint-doc", "maintainer-tool", total=1, families={"doc": 1}),
                    _row("scripts/driver", "driver-specific"),
                    _row("scripts/ok", "agentic-primitive", skill=1, total=1, families={"skill": 1}),
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_audit(tmp_path, ledger)

    assert report["schema_version"] == "script-exposure-audit/v1"
    assert report["status"] == "warn"
    assert report["summary"]["by_priority"] == {"P0": 1, "P1": 1, "P2": 1, "P3": 1, "OK": 1}
    markdown = render_markdown(report)
    assert "P0 agentic primitives without skill consumer: 1" in markdown
    assert "`scripts/agentic`" in markdown
