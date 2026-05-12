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
    maint_doc = classify_script(_row("scripts/maint-doc", "maintainer-tool", total=2, families={"doc": 1, "test": 1}))
    assert maint_doc["priority"] == "P2"
    assert maint_doc["exposure_class"] == "P2-evidence-only"
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


def test_documented_route_disposition_resolves_maintainer_runtime_route() -> None:
    row = _row("scripts/hooked-maintainer", "maintainer-tool", total=1, families={"hook": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/hooked-maintainer",
            "resolution": "documented_route",
            "route": "hooks/hooked-maintainer.sh",
            "rationale": "Synthetic maintainer route documentation.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-documented-route"


def test_internal_backend_disposition_resolves_p2_script_orchestrated() -> None:
    row = _row("scripts/internal_backend.py", "maintainer-tool", total=1, families={"script": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/internal_backend.py",
            "resolution": "internal_backend",
            "owner": "script-orchestrated backend",
            "rationale": "Synthetic backend classification.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["finding"] == "maintainer-tool-internal-backend"
    assert finding["exposure_class"] == "OK-internal-backend"


def test_operator_workflow_disposition_resolves_p2_script_orchestrated() -> None:
    row = _row("scripts/operator-workflow.sh", "maintainer-tool", total=1, families={"script": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/operator-workflow.sh",
            "resolution": "operator_workflow",
            "owner": "maintainer/operator workflow",
            "rationale": "Synthetic operator workflow classification.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-operator-workflow"


def test_documented_maintainer_disposition_resolves_doc_test_p2() -> None:
    row = _row("scripts/documented-tool", "maintainer-tool", total=2, families={"doc": 1, "test": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/documented-tool",
            "resolution": "documented_maintainer_tool",
            "evidence": "docs/tests evidence",
            "rationale": "Synthetic documented maintainer classification.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-documented-maintainer"


def test_test_fixture_disposition_resolves_test_only_p2() -> None:
    row = _row("scripts/test-fixture", "maintainer-tool", total=1, families={"test": 1})

    finding = classify_script(
        row,
        {
            "path": "scripts/test-fixture",
            "resolution": "test_fixture",
            "rationale": "Synthetic test fixture classification.",
        },
    )

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-test-fixture"


def test_explicit_maintainer_classification_resolves_p2() -> None:
    row = _row("scripts/internal", "maintainer-tool", total=2, families={"doc": 1, "test": 1})
    row["role_source"] = "override"
    row["override_rationale"] = "Synthetic internal maintainer tool."

    finding = classify_script(row)

    assert finding["priority"] == "OK"
    assert finding["exposure_class"] == "OK-classified-maintainer"


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
