#!/usr/bin/env python3
# SCOPE: os-only
"""Smoke portable primitive enforcement outside an IDE lifecycle."""
from __future__ import annotations
import os as _cos_os
import sys as _cos_sys
_cos_sys.path.insert(0, _cos_os.path.dirname(_cos_os.path.dirname(__file__)))

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.smoke_report_cli import run_smoke_report_cli

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "docs" / "06-Daily" / "reports" / "primitive-service-headless-smoke-latest.json"
DEFAULT_MD = ROOT / "docs" / "06-Daily" / "reports" / "primitive-service-headless-smoke-latest.md"


def _env(project: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "COGNITIVE_OS_PROJECT_DIR": str(project),
        "CLAUDE_PROJECT_DIR": str(project),
        "COGNITIVE_OS_SESSION_ID": "headless-smoke-session",
        "COGNITIVE_OS_TOOL_USE_ID": "headless-smoke-tool",
        "COGNITIVE_OS_HARNESS": "headless-smoke",
        "COGNITIVE_OS_HOOK_HEARTBEAT": "false",
    })
    for key in ("CI", "PYTEST_CURRENT_TEST", "COS_ALLOW_DESTRUCTIVE_GIT", "COS_GIT_BYPASS"):
        env.pop(key, None)
    return env


def _run_hook(project: Path, hook: str, payload: dict[str, Any]) -> dict[str, Any]:
    result = subprocess.run(
        ["bash", str(ROOT / "hooks" / hook)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=_env(project),
        cwd=str(ROOT),
        timeout=15,
    )
    return {
        "hook": hook,
        "returncode": result.returncode,
        "stderr_present": bool(result.stderr.strip()),
    }


def build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cos-headless-primitive-") as td:
        project = Path(td) / "consumer"
        (project / "lib").mkdir(parents=True)
        (project / "lib" / "duplicate_helper.py").write_text("print('existing')\n", encoding="utf-8")
        large = project / "large.txt"
        large.write_text("x" * 41000, encoding="utf-8")
        runs = [
            _run_hook(project, "destructive-git-blocker.sh", {"tool_name": "Bash", "tool_input": {"command": "git reset --hard private-headless"}}),
            _run_hook(project, "destructive-rm-blocker.sh", {"tool_name": "Bash", "tool_input": {"command": "rm -rf private-headless-dir"}}),
            _run_hook(project, "skill-router-bash-gate.sh", {"tool_name": "Bash", "tool_input": {"command": "pip install --upgrade private-headless-package"}}),
            _run_hook(project, "large-file-advisor.sh", {"tool_name": "Read", "tool_input": {"file_path": str(large)}}),
            _run_hook(project, "reinvention-check.sh", {"tool_name": "Agent", "tool_input": {"prompt": "create duplicate_helper.py in lib/ for a new hook"}}),
        ]
        ledger = project / ".cognitive-os" / "metrics" / "primitive-interventions.jsonl"
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.exists() else []
    by_id = {row.get("primitive_id") for row in rows}
    leaked = "private-headless" in json.dumps(rows) or "duplicate_helper" in json.dumps(rows)
    expected = {"destructive-git-blocker", "destructive-rm-blocker", "skill-router", "large-file-advisor", "reinvention-check"}
    status = "pass" if expected <= by_id and not leaked and any(run["returncode"] == 2 for run in runs) else "fail"
    return {
        "schema_version": "primitive-service-headless-smoke.v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "mode": "headless-shell-service-equivalent",
        "runs": runs,
        "ledger_row_count": len(rows),
        "primitive_ids": sorted(by_id),
        "content_free_rows": not leaked,
    }


def render_markdown(report: dict[str, Any]) -> str:
    return "\n".join([
        "# Primitive Service/Headless Smoke — Latest",
        "",
        f"Generated: {report['generated_at']}",
        f"Status: `{report['status']}`",
        f"Mode: `{report['mode']}`",
        f"Ledger rows: {report['ledger_row_count']}",
        f"Primitive ids: `{', '.join(report['primitive_ids'])}`",
        f"Content-free rows: `{report['content_free_rows']}`",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    return run_smoke_report_cli(
        argv,
        description=__doc__,
        build_report=build_report,
        render_markdown=render_markdown,
        default_json=DEFAULT_JSON,
        default_md=DEFAULT_MD,
        summary=lambda report: f"primitive-service-headless-smoke: {report['status']} rows={report['ledger_row_count']}",
    )

if __name__ == "__main__":
    raise SystemExit(main())
