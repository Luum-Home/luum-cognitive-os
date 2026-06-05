# SCOPE: os-only
"""Shared CLI runner for smoke scripts that emit optional reports."""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def run_smoke_report_cli(
    argv: list[str] | None,
    *,
    description: str | None,
    build_report: Callable[[], dict[str, Any]],
    render_markdown: Callable[[dict[str, Any]], str],
    default_json: Path,
    default_md: Path,
    summary: Callable[[dict[str, Any]], str],
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--json", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Run validation without updating tracked latest reports (default).")
    mode.add_argument("--write-report", action="store_true", help="Update tracked docs/06-Daily/reports/*-latest artifacts.")
    mode.add_argument("--no-write", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    report = build_report()
    if args.write_report:
        default_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        default_md.write_text(render_markdown(report), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(summary(report))
    return 0 if report["status"] == "pass" else 1
