#!/usr/bin/env python3
# SCOPE: both
"""Build and smoke a human-readable consumer `.ai/` package view.

This package is intentionally separate from the maintainer JSON overlay. It is
README-first Markdown generated from the same governed overlay data, and the
smoke writes only to a disposable consumer fixture.
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.portable_ai_overlay import build_overlay

SCHEMA_VERSION = "portable-ai-consumer-package.v1"
SMOKE_SCHEMA_VERSION = "portable-ai-consumer-package-smoke.v1"
DEFAULT_JSON = ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-consumer-package-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "06-Daily" / "reports" / "portable-ai-consumer-package-smoke-latest.md"


def _frontmatter(**values: object) -> str:
    lines = ["---"]
    for key, value in values.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"
        elif value is None:
            rendered = "null"
        elif isinstance(value, (int, float)):
            rendered = str(value)
        else:
            rendered = json.dumps(str(value), ensure_ascii=False)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _md_escape(text: object) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def _heading_id(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    return "-".join(part for part in safe.split("-") if part) or "item"


def _primitive_markdown(row: dict[str, Any], source_rel: str) -> str:
    contract = row.get("contract") or {}
    portable = row.get("portable_contract") or {}
    projection = portable.get("projection_fidelity") or contract.get("projection_fidelity") or {}
    lines = [
        _frontmatter(
            schema_version=SCHEMA_VERSION,
            package_role="human-readable-consumer-view",
            source_overlay_file=source_rel,
            portable_id=row.get("portable_id"),
            family=row.get("family"),
            contract_present=bool(contract.get("present")),
        ).rstrip(),
        "",
        f"# {_md_escape(row.get('portable_id'))}",
        "",
        f"Family: `{_md_escape(row.get('family'))}`  ",
        f"Canonical source: `{_md_escape(row.get('canonical_source'))}`  ",
        f"Overlay role: `{_md_escape(row.get('overlay_role'))}`",
        "",
        "## Intent",
        "",
        _md_escape(portable.get("intent") or contract.get("intent") or "No intent declared."),
        "",
        "## Projection fidelity",
        "",
    ]
    if projection:
        lines.extend(["| Harness | Fidelity | Runtime enforcement | Surface |", "|---|---|---:|---|"])
        for harness, item in sorted(projection.items()):
            if isinstance(item, dict):
                lines.append(
                    f"| `{_md_escape(harness)}` | `{_md_escape(item.get('fidelity'))}` | `{bool(item.get('claims_runtime_enforcement'))}` | {_md_escape(item.get('surface'))} |"
                )
    else:
        lines.append("No harness projection fidelity is declared for this primitive.")
    lines.extend(["", "## Evidence", ""])
    evidence = row.get("evidence") or {}
    commands = evidence.get("evidence_commands") or []
    if commands:
        for command in commands[:8]:
            lines.append(f"- `{_md_escape(command)}`")
    else:
        lines.append("- No evidence command listed in the overlay row.")
    lines.extend([
        "",
        "## Consumer boundary",
        "",
        "This Markdown file is advisory packaging. It does not claim runtime enforcement beyond the fidelity table above.",
        "",
    ])
    return "\n".join(lines)


def _adapter_markdown(row: dict[str, Any], source_rel: str) -> str:
    projected = row.get("projected_primitives") or []
    lines = [
        _frontmatter(
            schema_version=SCHEMA_VERSION,
            package_role="human-readable-consumer-view",
            source_overlay_file=source_rel,
            harness=row.get("harness"),
            proof_level=row.get("proof_level"),
        ).rstrip(),
        "",
        f"# {_md_escape(row.get('display_name') or row.get('harness'))} adapter",
        "",
        f"Harness: `{_md_escape(row.get('harness'))}`  ",
        f"Projection mode: `{_md_escape(row.get('projection_mode'))}`  ",
        f"Proof level: `{_md_escape(row.get('proof_level'))}`",
        "",
        "## Settings paths",
        "",
    ]
    for path in row.get("settings_paths") or []:
        lines.append(f"- `{_md_escape(path)}`")
    if not row.get("settings_paths"):
        lines.append("- none declared")
    fidelity_counts: dict[str, int] = {}
    for primitive in projected:
        if isinstance(primitive, dict):
            fidelity = str(primitive.get("fidelity") or "unknown")
            fidelity_counts[fidelity] = fidelity_counts.get(fidelity, 0) + 1
    lines.extend([
        "",
        "## Projected primitive summary",
        "",
        f"Projected primitives: `{len(projected)}`",
        "",
        "| Fidelity | Count |",
        "|---|---:|",
    ])
    if fidelity_counts:
        for fidelity, count in sorted(fidelity_counts.items()):
            lines.append(f"| `{_md_escape(fidelity)}` | {count} |")
    else:
        lines.append("| `none` | 0 |")
    lines.extend([
        "",
        "This adapter Markdown is generated from the declarative adapter manifest. It does not install host files by itself.",
        "",
    ])
    return "\n".join(lines)


def build_package(root: Path) -> dict[str, str]:
    """Return a README-first Markdown package suitable for a consumer `.ai/` tree."""
    overlay = build_overlay(root)
    context = json.loads(overlay["context.json"])
    primitive_items: list[tuple[str, dict[str, Any]]] = []
    adapter_items: list[tuple[str, dict[str, Any]]] = []
    for rel, body in overlay.items():
        if rel.startswith("primitives/") and rel.endswith(".json"):
            primitive_items.append((rel, json.loads(body)))
        elif rel.startswith("adapters/") and rel.endswith("/adapter.json"):
            adapter_items.append((rel, json.loads(body)))
    primitive_items.sort(key=lambda item: item[0])
    adapter_items.sort(key=lambda item: item[0])

    package: dict[str, str] = {}
    package["README.md"] = "\n".join([
        _frontmatter(schema_version=SCHEMA_VERSION, package_role="human-readable-consumer-view", generated_from="portable-ai-overlay.v1").rstrip(),
        "",
        "# Cognitive OS `.ai` consumer package",
        "",
        "This is the human-readable consumer view of Cognitive OS portable agentic primitives.",
        "It is generated from canonical COS manifests and the maintainer `.ai` overlay; edit canonical manifests, not this package.",
        "",
        "## Contents",
        "",
        "- `context/overview.md` — package policy, counts, and skill coverage boundary.",
        "- `primitives/INDEX.md` — primitive index grouped by family.",
        "- `adapters/INDEX.md` — harness adapter index and proof boundaries.",
        "",
        "## Enforcement boundary",
        "",
        "Markdown files are advisory unless a harness profile declares runtime-capable fidelity and the matching governed driver emits native files.",
        "",
    ])
    package["context/overview.md"] = "\n".join([
        _frontmatter(schema_version=SCHEMA_VERSION, package_role="human-readable-consumer-view").rstrip(),
        "",
        "# Package context",
        "",
        f"Overlay primitive rows: `{context.get('primitive_count')}`",
        f"Skill source count: `{context.get('skill_source_count')}`",
        f"Skill primitive rows: `{context.get('skill_overlay_count')}`",
        f"Skill rows excluded from primitive overlay: `{context.get('skill_overlay_excluded_count')}`",
        "",
        "## Policy",
        "",
        str(context.get("policy")),
        "",
        "## Consumer package policy",
        "",
        str(context.get("consumer_package_policy")),
        "",
    ])
    package["primitives/INDEX.md"] = "\n".join([
        _frontmatter(schema_version=SCHEMA_VERSION, package_role="human-readable-consumer-view").rstrip(),
        "",
        "# Primitive index",
        "",
        "| Primitive | Family | Contract | File |",
        "|---|---|---:|---|",
        *[
            f"| `{_md_escape(row.get('portable_id'))}` | `{_md_escape(row.get('family'))}` | `{bool((row.get('contract') or {}).get('present'))}` | [`{Path(rel).with_suffix('.md').as_posix()}`]({Path(rel).with_suffix('.md').as_posix().replace('primitives/', '')}) |"
            for rel, row in primitive_items
        ],
        "",
    ])
    package["adapters/INDEX.md"] = "\n".join([
        _frontmatter(schema_version=SCHEMA_VERSION, package_role="human-readable-consumer-view").rstrip(),
        "",
        "# Adapter index",
        "",
        "| Harness | Proof level | Projection mode | File |",
        "|---|---|---|---|",
        *[
            f"| `{_md_escape(row.get('harness'))}` | `{_md_escape(row.get('proof_level'))}` | `{_md_escape(row.get('projection_mode'))}` | [`{Path(rel).parent.name}.md`]({Path(rel).parent.name}.md) |"
            for rel, row in adapter_items
        ],
        "",
    ])

    for rel, row in primitive_items:
        md_rel = Path(rel).with_suffix(".md").as_posix()
        package[md_rel] = _primitive_markdown(row, rel)
    for rel, row in adapter_items:
        dirname = Path(rel).parent.name
        package[f"adapters/{dirname}.md"] = _adapter_markdown(row, rel)
    return dict(sorted(package.items()))


def build_report(root: Path) -> dict[str, Any]:
    package = build_package(root)
    overlay = build_overlay(root)
    primitive_overlay_count = sum(1 for path in overlay if path.startswith("primitives/") and path.endswith(".json"))
    adapter_overlay_count = sum(1 for path in overlay if path.startswith("adapters/") and path.endswith("/adapter.json"))
    with tempfile.TemporaryDirectory(prefix="cos-ai-consumer-package-") as td:
        consumer = Path(td) / "consumer"
        consumer.mkdir()
        for rel, body in package.items():
            target = consumer / ".ai" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        package_root = consumer / ".ai"
        markdown_files = sorted(package_root.rglob("*.md"))
        json_files = sorted(package_root.rglob("*.json"))
        frontmatter_files = [path for path in markdown_files if path.read_text(encoding="utf-8").startswith("---\n")]
        primitive_markdown_count = len(list((package_root / "primitives").rglob("*.md"))) - 1
        adapter_markdown_count = len(list((package_root / "adapters").glob("*.md"))) - 1
        no_canonical_mutation = not any((consumer / path).exists() for path in ("hooks", "skills", "rules", "manifests"))
        status = "pass" if (
            (package_root / "README.md").is_file()
            and (package_root / "context" / "overview.md").is_file()
            and primitive_markdown_count == primitive_overlay_count
            and adapter_markdown_count == adapter_overlay_count
            and not json_files
            and len(frontmatter_files) == len(markdown_files)
            and no_canonical_mutation
        ) else "fail"
        return {
            "schema_version": SMOKE_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "status": status,
            "consumer_fixture": "tempdir",
            "package_file_count": len(package),
            "markdown_file_count": len(markdown_files),
            "json_file_count": len(json_files),
            "primitive_markdown_count": primitive_markdown_count,
            "adapter_markdown_count": adapter_markdown_count,
            "primitive_overlay_count": primitive_overlay_count,
            "adapter_overlay_count": adapter_overlay_count,
            "frontmatter_file_count": len(frontmatter_files),
            "no_canonical_mutation": no_canonical_mutation,
        }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Portable `.ai` Consumer Package Smoke — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Schema: `{report['schema_version']}`",
        f"Status: `{report['status']}`",
        "",
        f"- package files: {report['package_file_count']}",
        f"- markdown files: {report['markdown_file_count']}",
        f"- JSON files: {report['json_file_count']}",
        f"- primitive Markdown files: {report['primitive_markdown_count']}",
        f"- adapter Markdown files: {report['adapter_markdown_count']}",
        f"- frontmatter files: {report['frontmatter_file_count']}",
        f"- no canonical mutation: `{report['no_canonical_mutation']}`",
        "",
        "This smoke writes a README-first Markdown `.ai` package to a disposable consumer fixture and verifies it remains packaging, not canonical COS state.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Run validation without updating tracked latest reports (default).")
    mode.add_argument("--write-report", action="store_true", help="Update tracked docs/06-Daily/reports/*-latest artifacts.")
    args = parser.parse_args(argv)
    root = args.project_dir.resolve()
    report = build_report(root)
    if args.write_report:
        DEFAULT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        DEFAULT_MD.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"portable-ai-consumer-package-smoke: {report['status']} files={report['package_file_count']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
