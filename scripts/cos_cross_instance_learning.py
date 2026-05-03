#!/usr/bin/env python3
# SCOPE: both
"""Cross-instance learning runway commands."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.cross_instance_learning import (
    audit_federation_triggers,
    audit_registry_locks,
    build_consumer_evidence,
    export_engram_bundle,
    import_consumer_evidence,
    propose_engram_import,
    write_registry_locks,
)


def _print(payload: dict) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") not in {"fail"} else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)

    export_evidence = sub.add_parser("export-consumer-evidence")
    export_evidence.add_argument("--project", required=True)
    export_evidence.add_argument("--reporter", required=True)
    export_evidence.add_argument("--profile", default="core")
    export_evidence.add_argument("--duration-days", type=int, default=0)
    export_evidence.add_argument("--cos-version", default="unknown")
    export_evidence.add_argument("--maintainer-owned", action="store_true")
    export_evidence.add_argument("--relationship", default="external-user")
    export_evidence.add_argument("--cognitive-cost", required=True)
    export_evidence.add_argument("--output", type=Path)

    import_evidence = sub.add_parser("import-consumer-evidence")
    import_evidence.add_argument("reports", nargs="+", type=Path)
    import_evidence.add_argument("--manifest", type=Path)

    registry = sub.add_parser("registry-lock")
    registry.add_argument("--write", action="store_true")
    registry.add_argument("--audit", action="store_true")

    engram_export = sub.add_parser("engram-export")
    engram_export.add_argument("--project", default="luum-cognitive-os")
    engram_export.add_argument("--max-entries", type=int, default=500)

    engram_import = sub.add_parser("engram-import-propose")
    engram_import.add_argument("bundle", type=Path)

    federation = sub.add_parser("federation-trigger-audit")
    federation.add_argument("--config", type=Path)

    args = parser.parse_args(argv)
    root = args.project_dir.resolve()

    if args.command == "export-consumer-evidence":
        report = build_consumer_evidence(
            root,
            project=args.project,
            reporter=args.reporter,
            profile=args.profile,
            duration_days=args.duration_days,
            cos_version=args.cos_version,
            maintainer_owned=args.maintainer_owned,
            relationship=args.relationship,
            cognitive_cost=args.cognitive_cost,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
            report["written_to"] = str(args.output)
        return _print({"status": "pass", "report": report})

    if args.command == "import-consumer-evidence":
        manifest = args.manifest or root / "manifests" / "external-adoption-evidence.yaml"
        return _print(import_consumer_evidence(manifest, [path.resolve() for path in args.reports]))

    if args.command == "registry-lock":
        if args.write:
            return _print({"status": "pass", **write_registry_locks(root)})
        return _print(audit_registry_locks(root))

    if args.command == "engram-export":
        return _print(export_engram_bundle(root, project=args.project, max_entries=args.max_entries))

    if args.command == "engram-import-propose":
        return _print(propose_engram_import(root, args.bundle.resolve()))

    if args.command == "federation-trigger-audit":
        config = args.config or root / "manifests" / "federation-triggers.yaml"
        return _print(audit_federation_triggers(config))

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
