from __future__ import annotations

import json
from pathlib import Path

from primitive_coverage.model import PrimitiveRow


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def merge_cos_audits(root: Path, rows: dict[str, PrimitiveRow]) -> None:
    row_audit = load_json(root / "docs" / "reports" / "primitive-row-audit-latest.json")
    for item in row_audit.get("rows", []):
        path = item.get("path")
        family = item.get("family")
        if not path or not family:
            continue
        key = f"{family}:{path}"
        row = rows.get(key)
        if row is None:
            continue
        row.metadata["cos_row_audit"] = {
            "status": item.get("status"),
            "severity": item.get("severity"),
            "next_action": item.get("next_action"),
        }
        evidence = str(item.get("evidence", ""))
        if "tested=True" in evidence:
            row.signals["tested"] = True
            row.signals["proof"] = True
        if "registered=True" in evidence or "wired=True" in evidence:
            row.signals["wired"] = True

    usage = load_json(root / "docs" / "reports" / "primitive-usage-map-latest.json")
    for item in usage.get("targets", []):
        path = item.get("path")
        if not path:
            continue
        for row in rows.values():
            if row.path == path:
                row.metadata["usage_map"] = {
                    "skill_consumers": item.get("skill_consumers"),
                    "total_consumers": item.get("total_consumers"),
                    "consumer_families": item.get("consumer_families", {}),
                }
                if item.get("total_consumers", 0) > 0:
                    row.signals["referenced"] = True
                break

    claims = load_json(root / "docs" / "reports" / "claim-proof-latest.json")
    for item in claims.get("rows", []):
        doc_path = item.get("path") or item.get("file")
        if not doc_path:
            continue
        for row in rows.values():
            if row.path == doc_path:
                row.claims.append(str(item.get("claim", "")).strip())
                if item.get("proof") or item.get("mapped") is True:
                    row.signals["proof"] = True
                break

    backlog = load_json(root / "docs" / "reports" / "reduction-backlog-latest.json")
    for item in backlog.get("items", []):
        path = item.get("path")
        family = item.get("family")
        key = f"{family}:{path}"
        if key in rows:
            rows[key].metadata["reduction_backlog"] = item
