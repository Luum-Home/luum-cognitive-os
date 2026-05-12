#!/usr/bin/env python3
# SCOPE: both
"""Smoke the generated `.ai` overlay against registered consumer shadows.

This proof is intentionally read-only for real consumer repositories. It reads the
COS installation registry, selects existing consumers for this source checkout,
and projects the generated overlay into temporary shadow directories that carry
consumer metadata. The smoke proves packaging compatibility without mutating the
actual projects.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _portable_path(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text.replace(str(Path.home()), "$HOME").replace(str(ROOT), "<repo-root>")


if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.consumer_fleet_audit import build_report as build_consumer_report
from scripts.portable_ai_overlay import build_overlay

SCHEMA_VERSION = "portable-ai-real-consumer-smoke.v1"
DEFAULT_JSON = ROOT / "docs" / "reports" / "portable-ai-real-consumer-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "reports" / "portable-ai-real-consumer-smoke-latest.md"


def _ai_snapshot(project: Path) -> dict[str, Any]:
    ai_dir = project / ".ai"
    if not ai_dir.exists():
        return {"exists": False, "file_count": 0, "mtime_ns_sum": 0}
    file_count = 0
    mtime_sum = 0
    try:
        for path in ai_dir.rglob("*"):
            if path.is_file():
                file_count += 1
                try:
                    mtime_sum += path.stat().st_mtime_ns
                except OSError:
                    pass
        return {"exists": True, "file_count": file_count, "mtime_ns_sum": mtime_sum}
    except OSError:
        return {"exists": True, "file_count": -1, "mtime_ns_sum": -1}


def _safe_consumer_id(project: dict[str, Any], index: int) -> str:
    raw = str(project.get("project_name") or f"consumer-{index}")
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in raw).strip("-")
    return safe[:80] or f"consumer-{index}"


def _candidate_projects(fleet: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    projects = [p for p in fleet.get("projects", []) if isinstance(p, dict) and p.get("exists")]
    projects.sort(key=lambda p: (str(p.get("status") or "warn") != "pass", str(p.get("project_name") or "")))
    return projects[:limit]


def _project_overlay(root: Path, overlay: dict[str, str], project: dict[str, Any], index: int, shadow_root: Path) -> dict[str, Any]:
    project_path = Path(str(project.get("path") or "")).expanduser()
    before = _ai_snapshot(project_path)
    shadow = shadow_root / _safe_consumer_id(project, index)
    shadow.mkdir(parents=True, exist_ok=True)
    (shadow / "consumer-metadata.json").write_text(
        json.dumps(
            {
                "project_name": project.get("project_name"),
                "harness": project.get("harness"),
                "registry_mode": project.get("registry_mode"),
                "effective_version": project.get("effective_version"),
                "source": "registered-consumer-shadow",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    for rel, body in overlay.items():
        target = shadow / ".ai" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    context = json.loads((shadow / ".ai" / "context.json").read_text(encoding="utf-8"))
    primitive_files = list((shadow / ".ai" / "primitives").rglob("*.json"))
    adapter_files = list((shadow / ".ai" / "adapters").glob("*/adapter.json"))
    profile_files = list((shadow / ".ai" / "profiles").glob("*.json"))
    no_canonical_shadow_mutation = not any((shadow / path).exists() for path in ("hooks", "skills", "rules", "manifests"))
    after = _ai_snapshot(project_path)
    actual_consumer_unchanged = before == after
    status = "pass" if primitive_files and adapter_files and profile_files and no_canonical_shadow_mutation and actual_consumer_unchanged and ("generated" in str(context.get("policy", "")) and "overlay" in str(context.get("policy", ""))) else "fail"
    return {
        "consumer_id": _safe_consumer_id(project, index),
        "status": status,
        "harness": str(project.get("harness") or "unknown"),
        "project_status": str(project.get("status") or "unknown"),
        "overlay_file_count": len(overlay),
        "primitive_file_count": len(primitive_files),
        "adapter_manifest_count": len(adapter_files),
        "profile_count": len(profile_files),
        "no_canonical_shadow_mutation": no_canonical_shadow_mutation,
        "actual_consumer_unchanged": actual_consumer_unchanged,
    }


def build_report(root: Path, registry_path: Path | None = None, limit: int = 2) -> dict[str, Any]:
    root = root.resolve()
    overlay = build_overlay(root)
    fleet = build_consumer_report(root, registry_path)
    candidates = _candidate_projects(fleet, limit)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="cos-portable-ai-real-consumers-") as td:
        shadow_root = Path(td)
        for index, project in enumerate(candidates, start=1):
            rows.append(_project_overlay(root, overlay, project, index, shadow_root))
    available = len([p for p in fleet.get("projects", []) if isinstance(p, dict) and p.get("exists")])
    passing = sum(1 for row in rows if row["status"] == "pass")
    if rows and passing == len(rows):
        status = "pass"
    elif not rows:
        status = "warn"
    else:
        status = "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "mode": "read-only-consumer-shadow",
        "registry_path": _portable_path(fleet.get("registry_path")),
        "source_dir": "<repo-root>",
        "available_consumer_count": available,
        "tested_consumer_count": len(rows),
        "passing_consumer_count": passing,
        "overlay_file_count": len(overlay),
        "consumer_rows": rows,
        "decision": {
            "mutates_real_consumers": False,
            "mutates_canonical_cos": False,
            "canonical_source": "manifests/primitive-contracts.yaml + COS primitive sources",
            "consumer_overlay_role": "generated .ai packaging proof",
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Portable `.ai` Real Consumer Smoke — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        f"Mode: `{report['mode']}`",
        "",
        f"- available registered consumers: {report['available_consumer_count']}",
        f"- tested consumer shadows: {report['tested_consumer_count']}",
        f"- passing shadows: {report['passing_consumer_count']}",
        f"- overlay files: {report['overlay_file_count']}",
        "",
        "## Consumer shadows",
        "",
        "| Consumer | Harness | Project status | Smoke | Primitive files | Actual unchanged |",
        "|---|---|---|---|---:|---|",
    ]
    for row in report.get("consumer_rows", []):
        lines.append(
            f"| `{row['consumer_id']}` | `{row['harness']}` | `{row['project_status']}` | `{row['status']}` | {row['primitive_file_count']} | `{row['actual_consumer_unchanged']}` |"
        )
    if not report.get("consumer_rows"):
        lines.append("| none | unknown | unknown | warn | 0 | `true` |")
    lines += [
        "",
        "This smoke never writes to registered consumer repositories. It projects the generated `.ai` overlay into temporary consumer shadows and checks the real consumer `.ai` snapshot is unchanged.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=2)
    parser.add_argument("--json", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Run validation without updating tracked latest reports (default).")
    mode.add_argument("--write-report", action="store_true", help="Update tracked docs/reports/*-latest artifacts.")
    args = parser.parse_args(argv)
    report = build_report(args.project_dir, args.registry, max(args.limit, 1))
    if args.write_report:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"portable-ai-real-consumer-smoke: {report['status']} tested={report['tested_consumer_count']}")
    return 0 if report["status"] in {"pass", "warn"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
