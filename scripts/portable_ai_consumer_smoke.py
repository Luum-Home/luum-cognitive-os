#!/usr/bin/env python3
# SCOPE: both
"""Smoke generated `.ai` overlay projection into a disposable consumer project."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.portable_ai_overlay import build_overlay

DEFAULT_JSON = ROOT / "docs" / "reports" / "portable-ai-consumer-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "reports" / "portable-ai-consumer-smoke-latest.md"


def build_report(root: Path) -> dict[str, Any]:
    overlay = build_overlay(root)
    with tempfile.TemporaryDirectory(prefix="cos-portable-ai-consumer-") as td:
        consumer = Path(td) / "consumer"
        consumer.mkdir()
        for rel, body in overlay.items():
            target = consumer / ".ai" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        context = json.loads((consumer / ".ai" / "context.json").read_text(encoding="utf-8"))
        primitive_files = sorted((consumer / ".ai" / "primitives").rglob("*.json"))
        adapter_files = sorted((consumer / ".ai" / "adapters").glob("*/adapter.json"))
        profile_files = sorted((consumer / ".ai" / "profiles").glob("*.json"))
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in primitive_files]
        registry_backed = sum(1 for row in rows if row.get("portable_contract", {}).get("source") == "primitive-contract-registry")
        lifecycle_derived = sum(1 for row in rows if row.get("portable_contract", {}).get("source") == "primitive-lifecycle-derived")
        no_canonical_mutation = not any((consumer / path).exists() for path in ("hooks", "skills", "rules", "manifests"))
        status = "pass" if primitive_files and adapter_files and profile_files and registry_backed >= 20 and lifecycle_derived >= 0 and no_canonical_mutation and context.get("policy", "").startswith("The `.ai` tree is a generated overlay") else "fail"
        return {
            "schema_version": "portable-ai-consumer-smoke.v1",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "status": status,
            "consumer_fixture": "tempdir",
            "overlay_file_count": len(overlay),
            "primitive_file_count": len(primitive_files),
            "adapter_manifest_count": len(adapter_files),
            "profile_count": len(profile_files),
            "registry_backed_count": registry_backed,
            "lifecycle_derived_count": lifecycle_derived,
            "no_canonical_mutation": no_canonical_mutation,
            "policy": context.get("policy"),
        }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Portable `.ai` Consumer Smoke — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        "",
        f"- overlay files: {report['overlay_file_count']}",
        f"- primitive files: {report['primitive_file_count']}",
        f"- adapter manifests: {report['adapter_manifest_count']}",
        f"- profiles: {report['profile_count']}",
        f"- registry-backed primitive rows: {report['registry_backed_count']}",
        f"- lifecycle-derived primitive rows: {report['lifecycle_derived_count']}",
        f"- no canonical mutation: `{report['no_canonical_mutation']}`",
        "",
        "This smoke writes the generated overlay to a disposable consumer fixture and verifies it remains packaging, not canonical COS state.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.project_dir.resolve())
    if not args.no_write:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"portable-ai-consumer-smoke: {report['status']} primitives={report['primitive_file_count']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
