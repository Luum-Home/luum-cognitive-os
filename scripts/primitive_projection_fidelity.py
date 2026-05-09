#!/usr/bin/env python3
# SCOPE: both
"""Generate ADR-256 primitive projection fidelity report.

This report joins the portable primitive contract registry with the existing
primitive harness coverage report. It does not promote contracts into runtime
proof; it compares declared fidelity against observed projection/wiring.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.primitive_contracts import load_contracts

SCHEMA_VERSION = "primitive-projection-fidelity.v1"
DEFAULT_COVERAGE = Path("docs/reports/primitive-harness-coverage-latest.json")
DEFAULT_JSON = Path("docs/reports/primitive-projection-fidelity-latest.json")
DEFAULT_MD = Path("docs/reports/primitive-projection-fidelity-latest.md")
DEFAULT_OPENCODE_SMOKE = Path("docs/reports/opencode-primitive-adapter-smoke-latest.json")
ENFORCED_FIDELITY = {"native-lifecycle-enforced", "governed-wrapper-enforced", "ci-enforced"}
NON_ENFORCED_FIDELITY = {"structural-advisory", "documented-only", "unsupported"}
PLUGIN_CAPABLE = "host-plugin-lifecycle-capable"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _coverage_by_primitive(root: Path, coverage_rel: Path = DEFAULT_COVERAGE) -> dict[str, dict[str, Any]]:
    coverage = _load_json(root / coverage_rel)
    out: dict[str, dict[str, Any]] = {}
    for item in coverage.get("items", []) or []:
        if isinstance(item, dict) and item.get("primitive"):
            out[str(item["primitive"])] = item
    return out


def _opencode_smoke_supported(root: Path, smoke_rel: Path = DEFAULT_OPENCODE_SMOKE) -> set[str]:
    smoke = _load_json(root / smoke_rel)
    if smoke.get("status") != "pass":
        return set()
    return {str(item) for item in smoke.get("supported_primitives", []) if item}


def _observed_state(coverage_row: dict[str, Any] | None, harness: str) -> dict[str, Any]:
    if not coverage_row:
        return {
            "installed": False,
            "projected": False,
            "wired": False,
            "behavior_proven": False,
            "observable": False,
            "operable": False,
            "evidence": [],
        }
    harnesses = coverage_row.get("harnesses", {}) or {}
    row = harnesses.get(harness, {}) or {}
    return {
        "installed": bool(row.get("installed")),
        "projected": bool(row.get("projected")),
        "wired": bool(row.get("wired")),
        "behavior_proven": bool(row.get("behavior_proven")),
        "observable": bool(row.get("observable")),
        "operable": bool(row.get("operable")),
        "evidence": list(row.get("evidence") or []),
    }


def _status_for(fidelity: str, observed: dict[str, Any]) -> tuple[str, str | None]:
    if fidelity in NON_ENFORCED_FIDELITY:
        return "aligned", None
    if fidelity == PLUGIN_CAPABLE:
        return "pending-runtime-smoke", "host plugin lifecycle declared but no signed runtime enforcement claimed"
    if fidelity in ENFORCED_FIDELITY:
        if observed["wired"] or observed["operable"] or observed["behavior_proven"]:
            return "aligned", None
        return "gap", "declared enforcement fidelity lacks observed wiring/behavior proof in harness coverage"
    return "unknown", f"unknown fidelity level: {fidelity}"


def build_report(root: Path) -> dict[str, Any]:
    coverage = _coverage_by_primitive(root)
    opencode_smoke_supported = _opencode_smoke_supported(root)
    items: list[dict[str, Any]] = []
    summary = {"contracts": 0, "projection_rows": 0, "aligned": 0, "gaps": 0, "pending_runtime_smoke": 0, "unknown": 0}

    for contract in load_contracts(root):
        contract_id = str(contract.get("id"))
        source = str(contract.get("source"))
        coverage_row = coverage.get(source)
        projections = []
        for harness, projection in sorted((contract.get("projection") or {}).items()):
            if not isinstance(projection, dict):
                continue
            fidelity = str(projection.get("fidelity", "unknown"))
            observed = _observed_state(coverage_row, str(harness))
            if str(harness) == "opencode" and contract_id in opencode_smoke_supported:
                observed = {
                    **observed,
                    "installed": True,
                    "projected": True,
                    "wired": True,
                    "behavior_proven": True,
                    "observable": True,
                    "operable": True,
                    "evidence": sorted(set(observed.get("evidence", [])) | {"opencode-plugin-smoke"}),
                }
            status, finding = _status_for(fidelity, observed)
            summary["projection_rows"] += 1
            if status == "aligned":
                summary["aligned"] += 1
            elif status == "gap":
                summary["gaps"] += 1
            elif status == "pending-runtime-smoke":
                summary["pending_runtime_smoke"] += 1
            else:
                summary["unknown"] += 1
            projections.append({
                "harness": str(harness),
                "declared_fidelity": fidelity,
                "declared_surface": projection.get("surface"),
                "status": status,
                "finding": finding,
                "observed": observed,
            })
        summary["contracts"] += 1
        items.append({
            "contract_id": contract_id,
            "source": source,
            "family": contract.get("family"),
            "intent": contract.get("intent"),
            "consumer_fleet_impact": (contract.get("impact") or {}).get("consumer_fleet"),
            "service_mode_impact": (contract.get("impact") or {}).get("service_mode"),
            "coverage_present": coverage_row is not None,
            "projection_fidelity": projections,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "purpose": "Join primitive contracts to observed harness coverage without treating declared contracts as runtime proof.",
        "summary": summary,
        "items": items,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Primitive Projection Fidelity — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Schema: `{report['schema_version']}`",
        "",
        "This report compares declared primitive contract fidelity with observed harness coverage. Declared contracts are not runtime proof.",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Contracts", ""])
    for item in report["items"]:
        lines.append(f"### `{item['contract_id']}`")
        lines.append(f"- source: `{item['source']}`")
        lines.append(f"- consumer fleet impact: `{item.get('consumer_fleet_impact')}`")
        lines.append(f"- service mode impact: `{item.get('service_mode_impact')}`")
        for row in item["projection_fidelity"]:
            suffix = f" — {row['finding']}" if row.get("finding") else ""
            lines.append(f"  - {row['harness']}: `{row['declared_fidelity']}` → `{row['status']}`{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--print-json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.project_dir).resolve()
    report = build_report(root)
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    if not args.no_write:
        json_path = root / DEFAULT_JSON
        md_path = root / DEFAULT_MD
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
