"""ADR-208 imported pattern closure audit."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = "imported-pattern-closure-audit/v1"


def load_manifest(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "imported-pattern-closures/v1":
        raise ValueError(f"invalid imported pattern closure manifest: {path}")
    return payload


def audit(path: Path) -> dict[str, Any]:
    manifest = load_manifest(path)
    policy = manifest.get("policy", {}) or {}
    required = [str(item) for item in policy.get("required_fields", [])]
    promoted = set(str(item) for item in policy.get("promoted_states_require_closure", []))
    findings: list[dict[str, Any]] = []
    closures = [item for item in manifest.get("closures", []) if isinstance(item, dict)]
    for closure in closures:
        cid = str(closure.get("id") or "<unknown>")
        missing = [field for field in required if not closure.get(field)]
        status = str(closure.get("status") or "lab")
        if missing:
            findings.append(
                {
                    "severity": "block" if status in promoted else "warn",
                    "code": "closure-required-fields-missing",
                    "id": cid,
                    "status": status,
                    "missing_fields": missing,
                    "message": "Imported pattern closure is missing producer/consumer/scheduler/evaluator ownership fields.",
                }
            )
        if status in promoted and missing:
            continue
    block_count = sum(1 for f in findings if f["severity"] == "block")
    warn_count = sum(1 for f in findings if f["severity"] == "warn")
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest": str(path),
        "status": "fail" if block_count else "warn" if warn_count else "pass",
        "closure_count": len(closures),
        "block_count": block_count,
        "warn_count": warn_count,
        "findings": findings,
        "policy": "Imported patterns may not be promoted beyond lab/sandbox unless producer, consumer, scheduler, evaluator, owner, tests, and demotion path are declared.",
    }

