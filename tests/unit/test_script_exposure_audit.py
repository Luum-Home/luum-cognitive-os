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


def _row_with_consumers(path: str, role: str, consumers: list[dict[str, str]]) -> dict:
    families: dict[str, int] = {}
    for consumer in consumers:
        families[consumer["family"]] = families.get(consumer["family"], 0) + 1
    return {
        "path": path,
        "role": role,
        "skill_consumers": 0,
        "total_consumers": len(consumers),
        "consumer_families": families,
        "consumers": consumers,
    }


def test_classify_script_priorities() -> None:
    unrouted = classify_script(_row("scripts/agentic", "agentic-primitive"))
    assert unrouted["priority"] == "P0"
    assert unrouted["exposure_class"] == "P0-unrouted"

    routed = classify_script(_row("scripts/agentic-hooked", "agentic-primitive", total=1, families={"hook": 1}))
    assert routed["priority"] == "P0"
    assert routed["exposure_class"] == "P0-route-undocumented"

    promoted = classify_script(_row("scripts/agentic-tested", "agentic-primitive", total=1, families={"test": 1}))
    assert promoted["priority"] == "P0"
    assert promoted["exposure_class"] == "P0-promotion-candidate"

    assert classify_script(_row("scripts/maint", "maintainer-tool"))["priority"] == "P1"
    assert classify_script(_row("scripts/maint-doc", "maintainer-tool", total=2, families={"doc": 1, "test": 1}))["priority"] == "P2"
    assert classify_script(_row("scripts/lab", "lab"))["priority"] == "P3"
    assert classify_script(_row("scripts/skilled", "agentic-primitive", skill=1, total=1, families={"skill": 1}))["priority"] == "OK"


def test_router_detection_is_conservative() -> None:
    routed = classify_script(
        _row_with_consumers("scripts/target", "agentic-primitive", [{"family": "script", "path": "scripts/cos"}])
    )
    assert routed["exposure_class"] == "P0-route-undocumented"
    assert routed["channels"]["router"] == 1

    sibling_cos_script = classify_script(
        _row_with_consumers("scripts/target", "agentic-primitive", [{"family": "script", "path": "scripts/cos-ci-local.sh"}])
    )
    assert sibling_cos_script["exposure_class"] == "P0-promotion-candidate"
    assert sibling_cos_script["channels"]["router"] == 0


def test_documented_route_disposition_resolves_p0() -> None:
    row = _row("scripts/hooked", "agentic-primitive", total=1, families={"hook": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/hooked",
            "resolution": "documented_route",
            "route": "hooks/hooked.sh",
            "rationale": "Synthetic route documentation.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-documented-route"
    assert finding["disposition"]["resolution"] == "documented_route"


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
    assert report["summary"]["by_exposure_class"]["P0-unrouted"] == 1
    markdown = render_markdown(report)
    assert "P0 agentic primitives without skill consumer: 1" in markdown
    assert "P0 unrouted: 1" in markdown
    assert "`scripts/agentic`" in markdown
